//! YAML 1.2 block presentation of an already-admitted JSON response.
use serde_json::Value;
use std::{collections::HashMap, fmt::Write};

#[derive(Default)]
struct Occurrence {
    repeated: bool,
    anchor: Option<usize>,
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

fn string(value: &str, flow: bool) -> String {
    // Restrict plain scalars to an unambiguous subset that works in collections
    // and with YAML 1.1 readers. Quote anything with structural punctuation.
    let starts_as_text = value
        .as_bytes()
        .first()
        .is_some_and(u8::is_ascii_alphabetic)
        || value.starts_with(['/', '_', '$', '\\'])
        || value
            .strip_prefix('.')
            .and_then(|s| s.as_bytes().first())
            .is_some_and(u8::is_ascii_alphabetic);
    let plain = starts_as_text
        && !value.ends_with([' ', ':'])
        && !value.contains(": ")
        && !value.contains(" #")
        && !(flow && value.contains(['[', ']', '{', '}', ',']))
        && !matches!(
            value.to_ascii_lowercase().as_str(),
            "true" | "false" | "null" | "yes" | "no" | "on" | "off" | "y" | "n" | ".inf" | ".nan"
        )
        && value
            .bytes()
            .all(|byte| byte == b' ' || byte.is_ascii_graphic());
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

fn scalar(value: &Value, flow: bool) -> String {
    match value {
        Value::String(text) => string(text, flow),
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

fn literal_style(value: &str) -> Option<&'static str> {
    // Use implicit indentation only when the first content line establishes it.
    let first = value.trim_start_matches('\n').chars().next()?;
    if !value.contains('\n')
        || first.is_whitespace()
        || value.chars().any(|ch| {
            (ch.is_control() && ch != '\n')
                || matches!(
                    ch,
                    '\u{2028}' | '\u{2029}' | '\u{feff}' | '\u{fffe}' | '\u{ffff}'
                )
        })
    {
        return None;
    }
    Some(if value.ends_with("\n\n") {
        "|+"
    } else if value.ends_with('\n') {
        "|"
    } else {
        "|-"
    })
}

// Bound the expansion of nested aliases under the standard yaml reader's
// default limit. A definition may itself contain references to earlier values.
const MAX_ALIAS_EXPANSION: usize = 100;

#[derive(Default)]
struct Anchor {
    // Indices into the document's alias stream, including nested definitions.
    contents: std::ops::Range<usize>,
    uses: usize, // includes the definition
    expansion: Option<usize>,
}

#[derive(Default)]
struct Document {
    occurrences: HashMap<String, Occurrence>,
    anchors: Vec<Anchor>,
    aliases: Vec<usize>,
    text: String,
}

enum Presentation {
    Literal,
    Definition(usize),
    Alias(usize),
}

impl Document {
    fn presentation(&mut self, value: &Value) -> Presentation {
        let key = value.to_string();
        let Some(item) = self.occurrences.get_mut(&key).filter(|v| v.repeated) else {
            return Presentation::Literal;
        };
        let Some(id) = item.anchor else {
            let id = self.anchors.len();
            item.anchor = Some(id);
            self.anchors.push(Anchor {
                uses: 1,
                ..Anchor::default()
            });
            return Presentation::Definition(id);
        };
        let anchor = &self.anchors[id];
        // Readers evaluate an anchor's nested expansion at its first alias.
        // Earlier aliases can acquire more uses between definition and use.
        let expansion = anchor.expansion.unwrap_or_else(|| {
            self.aliases[anchor.contents.clone()]
                .iter()
                .map(|&child| {
                    let nested = &self.anchors[child];
                    nested.uses * nested.expansion.expect("already referenced")
                })
                .max()
                .unwrap_or(1)
        });
        let anchor = &mut self.anchors[id];
        anchor.expansion = Some(expansion);
        if (anchor.uses + 1) * expansion > MAX_ALIAS_EXPANSION {
            return Presentation::Literal;
        }
        anchor.uses += 1;
        self.aliases.push(id);
        Presentation::Alias(id)
    }

    fn inline_scalar(&mut self, value: &Value) -> String {
        match self.presentation(value) {
            Presentation::Alias(id) => format!("*{}", anchor_name(id + 1)),
            Presentation::Definition(id) => {
                format!("&{} {}", anchor_name(id + 1), scalar(value, true))
            }
            Presentation::Literal => scalar(value, true),
        }
    }

    fn node(&mut self, value: &Value, indent: usize, prefix: &str) {
        let id = match self.presentation(value) {
            Presentation::Alias(id) => {
                self.line(indent, prefix, &format!("*{}", anchor_name(id + 1)));
                return;
            }
            Presentation::Definition(id) => Some(id),
            Presentation::Literal => None,
        };
        let definition = id
            .map(|i| format!("&{}", anchor_name(i + 1)))
            .unwrap_or_default();
        let begin = self.aliases.len();
        if let Some((text, style)) = value
            .as_str()
            .and_then(|s| literal_style(s).map(|style| (s, style)))
        {
            let body = if definition.is_empty() {
                style.to_owned()
            } else {
                format!("{definition} {style}")
            };
            self.line(indent, prefix, &body);
            for line in text.split_terminator('\n') {
                if line.is_empty() {
                    self.text.push('\n');
                } else {
                    self.line(indent + 1, "", line);
                }
            }
        } else if !block(value) {
            let inline = match value {
                Value::Array(items) => format!(
                    "[{}]",
                    items
                        .iter()
                        .map(|item| self.inline_scalar(item))
                        .collect::<Vec<_>>()
                        .join(", ")
                ),
                _ => scalar(value, false),
            };
            let body = if definition.is_empty() {
                inline
            } else {
                format!("{definition} {inline}")
            };
            self.line(indent, prefix, &body);
        } else {
            let compact_map = prefix == "-" && id.is_none() && value.is_object();
            if compact_map {
                write!(self.text, "{:indent$}- ", "").unwrap();
            } else if !prefix.is_empty() || !definition.is_empty() {
                self.line(indent, prefix, &definition);
            }
            let indent_required =
                !prefix.is_empty() && !(value.is_array() && prefix.ends_with(':'));
            let child_indent = indent + usize::from(indent_required) + usize::from(compact_map);
            match value {
                Value::Object(fields) => {
                    for (key, child) in fields {
                        let key = string(key, false);
                        let prefix = if key.len() > 1024 {
                            self.line(child_indent, "?", &key);
                            ":".to_owned()
                        } else {
                            format!("{key}:")
                        };
                        self.node(child, child_indent, &prefix);
                    }
                }
                Value::Array(items) => {
                    for child in items {
                        self.node(child, child_indent, "-");
                    }
                }
                _ => unreachable!("only nonempty collections use block style"),
            }
        }
        if let Some(id) = id {
            self.anchors[id].contents = begin..self.aliases.len();
        }
    }

    fn line(&mut self, indent: usize, prefix: &str, body: &str) {
        // A compact sequence mapping has already written the first key's "- ".
        if self.text.is_empty() || self.text.ends_with('\n') {
            write!(self.text, "{:indent$}", "").unwrap();
        }
        self.text.push_str(prefix);
        if !prefix.is_empty() && !body.is_empty() {
            self.text.push(' ');
        }
        writeln!(self.text, "{body}").unwrap();
    }
}

pub(super) fn render(value: &Value) -> String {
    let mut document = Document::default();
    count(value, &mut document.occurrences);
    document.node(value, 0, "");
    document.text
}
