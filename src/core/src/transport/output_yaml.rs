//! YAML 1.2 block presentation of an already-admitted JSON response.
use serde_json::Value;
use std::{collections::HashMap, fmt::Write};

#[derive(Default)]
struct Occurrence {
    repeated: bool,
    anchor: String,
    aliases: usize,
}

fn count(value: &Value, occurrences: &mut HashMap<String, Occurrence>) {
    let key = value.to_string();
    if key.len() >= 24 {
        if let Some(previous) = occurrences.get_mut(&key) {
            previous.repeated = true;
            return;
        }
        occurrences.insert(key, Occurrence::default());
    }
    match value {
        Value::Array(items) => items.iter().for_each(|item| count(item, occurrences)),
        Value::Object(fields) => fields.values().for_each(|item| count(item, occurrences)),
        _ => {}
    }
}

fn anchor_name(mut index: usize) -> String {
    let mut name = Vec::new();
    while index > 0 {
        index -= 1;
        name.push(char::from(b'a' + (index % 26) as u8));
        index /= 26;
    }
    name.into_iter().rev().collect()
}

fn string(value: &str) -> String {
    // Restrict plain scalars to an unambiguous subset that works in collections
    // and with YAML 1.1 readers. Quote anything with structural punctuation.
    let plain = value
        .as_bytes()
        .first()
        .is_some_and(u8::is_ascii_alphabetic)
        && !value.ends_with([' ', ':'])
        && !value.contains(": ")
        && !matches!(
            value.to_ascii_lowercase().as_str(),
            "true" | "false" | "null" | "yes" | "no" | "on" | "off" | "y" | "n"
        )
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b" _./:@-".contains(&byte));
    if plain {
        return value.to_owned();
    }
    // JSON escapes the C0 range. YAML also reserves these nonprinting and
    // legacy line-separator code points, which JSON can emit literally.
    let mut quoted = String::new();
    for character in serde_json::to_string(value)
        .expect("string is JSON")
        .chars()
    {
        match character {
            '\u{7f}'..='\u{9f}'
            | '\u{2028}'
            | '\u{2029}'
            | '\u{feff}'
            | '\u{fffe}'
            | '\u{ffff}' => {
                write!(quoted, "\\u{:04x}", u32::from(character)).unwrap();
            }
            _ => quoted.push(character),
        }
    }
    quoted
}

fn scalar(value: &Value) -> String {
    match value {
        Value::String(text) => string(text),
        Value::Number(number) if number.is_f64() => {
            let decimal = number.to_string();
            if let Some((mantissa, exponent)) = decimal.split_once('e') {
                let fraction = if mantissa.contains('.') { "" } else { ".0" };
                let sign = if exponent.starts_with(['+', '-']) {
                    ""
                } else {
                    "+"
                };
                format!("{mantissa}{fraction}e{sign}{exponent}")
            } else {
                decimal
            }
        }
        _ => value.to_string(),
    }
}

fn block(value: &Value) -> bool {
    match value {
        Value::Object(fields) => !fields.is_empty(),
        Value::Array(items) => {
            !items.is_empty()
                && (items.len() > 12
                    || items.iter().any(|item| item.is_array() || item.is_object())
                    || value.to_string().len() > 200)
        }
        _ => false,
    }
}

#[derive(Default)]
struct Document {
    occurrences: HashMap<String, Occurrence>,
    anchors: usize,
    text: String,
}

impl Document {
    fn node(&mut self, value: &Value, indent: usize, prefix: &str, inside_anchor: bool) {
        let anchor = if inside_anchor {
            None
        } else {
            self.occurrences
                .get_mut(&value.to_string())
                .filter(|item| item.repeated)
        };
        let mut definition = String::new();
        if let Some(item) = anchor {
            if item.anchor.is_empty() {
                self.anchors += 1;
                item.anchor = anchor_name(self.anchors);
                definition = format!("&{}", item.anchor);
            } else if item.aliases < 32 {
                item.aliases += 1;
                let alias = format!("*{}", item.anchor);
                self.line(indent, prefix, &alias);
                return;
            }
        }
        if !block(value) {
            let inline = match value {
                Value::Array(items) => format!(
                    "[{}]",
                    items.iter().map(scalar).collect::<Vec<_>>().join(",")
                ),
                _ => scalar(value),
            };
            let body = if definition.is_empty() {
                inline
            } else {
                format!("{definition} {inline}")
            };
            self.line(indent, prefix, &body);
            return;
        }
        if !prefix.is_empty() || !definition.is_empty() {
            self.line(indent, prefix, &definition);
        }
        let children_inside_anchor = inside_anchor || !definition.is_empty();
        let indent_required = !prefix.is_empty() && !(value.is_array() && prefix.ends_with(':'));
        let child_indent = indent + usize::from(indent_required);
        match value {
            Value::Object(fields) => {
                for (key, child) in fields {
                    let key = string(key);
                    let prefix = if key.len() > 1024 {
                        self.line(child_indent, "?", &key);
                        ":".to_owned()
                    } else {
                        format!("{key}:")
                    };
                    self.node(child, child_indent, &prefix, children_inside_anchor);
                }
            }
            Value::Array(items) => {
                for child in items {
                    self.node(child, child_indent, "-", children_inside_anchor);
                }
            }
            _ => unreachable!("only nonempty collections use block style"),
        }
    }

    fn line(&mut self, indent: usize, prefix: &str, body: &str) {
        write!(self.text, "{:indent$}{prefix}", "").unwrap();
        if !prefix.is_empty() && !body.is_empty() {
            self.text.push(' ');
        }
        writeln!(self.text, "{body}").unwrap();
    }
}

pub(super) fn render(value: &Value) -> String {
    let mut document = Document::default();
    count(value, &mut document.occurrences);
    // Avoid aliases inside anchors. This bounds expansion and allows clients
    // to keep their normal parser alias protections enabled.
    document.node(value, 0, "", false);
    document.text
}
