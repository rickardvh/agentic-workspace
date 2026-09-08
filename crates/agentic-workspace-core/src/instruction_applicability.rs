//! Shared scoped applicability. Inputs describe current scope and agent-selected
//! routes; this owner supplies no binding, execution or evidence authority.
use crate::{CoreError, route_ids};
use serde::Deserialize;
use serde_json::{Value, json};
use std::collections::BTreeSet;

enum Token {
    Star,
    Any,
    Literal(char),
    Class(bool, Vec<(char, char)>),
}

/// Python fnmatch path semantics: stars span separators, bracket classes use
/// ranges and ! negation, and unmatched '[' is literal. Match host normcase.
fn tokens(pattern: &str) -> Vec<Token> {
    #[cfg(windows)]
    let pattern = pattern.replace('\\', "/").to_lowercase();
    let chars: Vec<char> = pattern.chars().collect();
    let mut tokens = Vec::new();
    let mut i = 0;
    while i < chars.len() {
        let token = match chars[i] {
            '*' => Token::Star,
            '?' => Token::Any,
            '[' => {
                let start = i + 1;
                let mut end = start;
                if chars.get(end) == Some(&'!') {
                    end += 1;
                }
                if chars.get(end) == Some(&']') {
                    end += 1;
                }
                while end < chars.len() && chars[end] != ']' {
                    end += 1;
                }
                if end == chars.len() {
                    Token::Literal('[')
                } else {
                    let negated = chars.get(start) == Some(&'!');
                    let mut j = start + usize::from(negated);
                    let mut ranges = Vec::new();
                    while j < end {
                        if j + 2 < end && chars[j + 1] == '-' {
                            ranges.push((chars[j], chars[j + 2]));
                            j += 3;
                        } else {
                            ranges.push((chars[j], chars[j]));
                            j += 1;
                        }
                    }
                    i = end;
                    Token::Class(negated, ranges)
                }
            }
            literal => Token::Literal(literal),
        };
        tokens.push(token);
        i += 1;
    }
    tokens
}

pub(crate) fn matches(pattern: &str, path: &str) -> bool {
    #[cfg(windows)]
    let path = path.replace('\\', "/").to_lowercase();
    let path: Vec<char> = path.chars().collect();
    let mut row = vec![false; path.len() + 1];
    row[0] = true;
    for token in tokens(pattern) {
        let mut next = vec![false; row.len()];
        next[0] = matches!(token, Token::Star) && row[0];
        for (i, ch) in path.iter().enumerate() {
            next[i + 1] = match &token {
                Token::Star => next[i] || row[i + 1],
                Token::Any => row[i],
                Token::Literal(c) => row[i] && ch == c,
                Token::Class(negated, ranges) => {
                    row[i] && (ranges.iter().any(|(a, b)| a <= ch && ch <= b) != *negated)
                }
            };
        }
        row = next;
    }
    *row.last().unwrap()
}

fn accepts(token: &Token, ch: char) -> bool {
    match token {
        Token::Star | Token::Any => true,
        Token::Literal(value) => *value == ch,
        Token::Class(negated, ranges) => {
            ranges.iter().any(|(a, b)| *a <= ch && ch <= *b) != *negated
        }
    }
}

fn intersect(left: &Token, right: &Token) -> bool {
    // Membership changes only at a literal/range boundary. Test those finite
    // intervals instead of enumerating Unicode or inventing a second matcher.
    let mut boundaries = vec![0, 0xe000];
    for token in [left, right] {
        let ranges = match token {
            Token::Literal(c) => vec![(*c, *c)],
            Token::Class(_, ranges) => ranges.clone(),
            _ => vec![],
        };
        for (a, b) in ranges {
            if a <= b {
                boundaries.push(a as u32);
                if (b as u32) < 0x10ffff {
                    boundaries.push(b as u32 + 1);
                }
            }
        }
    }
    boundaries
        .into_iter()
        .filter_map(char::from_u32)
        .any(|ch| accepts(left, ch) && accepts(right, ch))
}

/// Nonempty intersection of two fnmatch languages, using the same tokens as
/// exact path matching. Star epsilon transitions keep the pair-state walk finite.
pub(crate) fn patterns_overlap(left: &str, right: &str) -> bool {
    let left = tokens(left);
    let right = tokens(right);
    let mut pending = vec![(0, 0)];
    let mut seen = BTreeSet::new();
    while let Some((a, b)) = pending.pop() {
        if !seen.insert((a, b)) {
            continue;
        }
        if a == left.len() && b == right.len() {
            return true;
        }
        if matches!(left.get(a), Some(Token::Star)) {
            pending.push((a + 1, b));
        }
        if matches!(right.get(b), Some(Token::Star)) {
            pending.push((a, b + 1));
        }
        if let (Some(l), Some(r)) = (left.get(a), right.get(b))
            && intersect(l, r)
        {
            pending.push((
                a + usize::from(!matches!(l, Token::Star)),
                b + usize::from(!matches!(r, Token::Star)),
            ));
        }
    }
    false
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    paths: Vec<String>,
    routes: Vec<String>,
    changed_paths: Vec<String>,
    selected_routes: Vec<String>,
    route_posture: String,
}

pub fn view(value: Value) -> Result<Value, CoreError> {
    let schema: Value = serde_json::from_str(include_str!(
        "../../../src/agentic_workspace/contracts/schemas/instruction_applicability.schema.json"
    ))
    .expect("checked schema");
    crate::schema_validator(&schema, "instruction applicability")?
        .validate(&value)
        .map_err(|e| CoreError::new(e.to_string()))?;
    let input: Input = serde_json::from_value(value).map_err(|e| CoreError::new(e.to_string()))?;
    let selected: Vec<String> = input
        .selected_routes
        .iter()
        .map(|r| r.trim().trim_matches('/').to_owned())
        .collect();
    route_ids(selected.clone(), "instruction selected routes")?;
    let selectors: Vec<String> = input
        .routes
        .iter()
        .map(|r| r.trim().trim_matches('/').to_owned())
        .collect();
    route_ids(
        selectors
            .iter()
            .map(|r| r.strip_suffix("/**").unwrap_or(r).to_owned())
            .collect(),
        "instruction selectors",
    )?;
    let matched: Vec<String> = input
        .changed_paths
        .iter()
        .map(|p| p.replace('\\', "/"))
        .filter(|p| input.paths.iter().any(|pattern| matches(pattern, p)))
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    let path_applies = input.paths.is_empty() || !matched.is_empty();
    let route_applies = input.routes.is_empty()
        || (input.route_posture == "selected"
            && selectors.iter().any(|selector| {
                selected.iter().any(|route| {
                    selector
                        .strip_suffix("/**")
                        .map_or(route == selector, |prefix| {
                            route == prefix || route.starts_with(&format!("{prefix}/"))
                        })
                })
            }));
    let applies = path_applies && route_applies;
    let mut reasons = Vec::new();
    if applies {
        if input.paths.is_empty() {
            reasons.push("global path scope".to_owned());
        } else {
            let pattern = input
                .paths
                .iter()
                .find(|pattern| matches(pattern, &matched[0]))
                .unwrap();
            reasons.push(format!("{} matches {pattern}", matched[0]));
        }
        if !input.routes.is_empty() {
            reasons.push(format!(
                "selected semantic route matches {}",
                input.routes.join(", ")
            ));
        }
    } else {
        if !path_applies {
            reasons.push(format!(
                "no changed or target path matches {}",
                input.paths.join(", ")
            ));
        }
        if !route_applies {
            reasons.push(if input.route_posture != "selected" {
                format!("semantic route selection is {}", input.route_posture)
            } else {
                format!(
                    "no selected semantic route matches {}",
                    input.routes.join(", ")
                )
            });
        }
    }
    Ok(
        json!({"applies":applies,"path_applies":path_applies,"route_applies":route_applies,"reason":reasons.join("; "),"matched_paths":matched}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn instruction_fnmatch_classes_and_separator_semantics() {
        for (pattern, path, expected) in [
            ("src/[ab]?.py", "src/a1.py", true),
            ("src/[!a-c]*", "src/deep/file", true),
            ("src/[!a-c]*", "src/bfile", false),
            ("[[]*", "[name", true),
            ("[]]", "]", true),
            ("[abc", "[abc", true),
            ("[z-a]", "z", false),
            ("[-a]", "-", true),
            ("[a-]", "-", true),
            ("src/*", "src/deep/file", true),
        ] {
            assert_eq!(matches(pattern, path), expected, "{pattern} {path}");
        }
    }
    #[test]
    fn instruction_pattern_intersection_uses_same_classes() {
        for (left, right, expected) in [
            ("src/[a-c]*", "src/[d-f]*", false),
            ("src/[!a-c]*", "src/[d-f]*", true),
            ("[!a]", "a", false),
            ("[a-z]", "[!a-z]", false),
            ("[[]*", "[name", true),
            (
                ".agentic-workspace/local/planning/owner-selection.*.*.tmp",
                ".agentic-workspace/local/planning/owner-selection.[0-9]*.tmp",
                true,
            ),
            ("*.tmp", "*.json", false),
            ("[z-a]", "*", false),
        ] {
            assert_eq!(patterns_overlap(left, right), expected, "{left} {right}");
            assert_eq!(patterns_overlap(right, left), expected);
        }
    }
    #[test]
    fn instruction_applicability_preserves_and_reasons_and_validates_routes() {
        let mut input = json!({"paths":["src/auth/**"],"routes":["workspace/ownership/**"],"changed_paths":["src/auth/token.py"],"selected_routes":[],"route_posture":"unresolved"});
        assert_eq!(
            view(input.clone()).unwrap()["reason"],
            "semantic route selection is unresolved"
        );
        input["route_posture"] = json!("selected");
        input["selected_routes"] = json!(["workspace/ownership/audit"]);
        let output = view(input.clone()).unwrap();
        assert_eq!(output["applies"], true);
        assert_eq!(
            output["reason"],
            "src/auth/token.py matches src/auth/**; selected semantic route matches workspace/ownership/**"
        );
        input["changed_paths"] = json!(["other.txt"]);
        assert_eq!(view(input.clone()).unwrap()["applies"], false);
        input["selected_routes"] = json!(["task words"]);
        assert!(view(input).is_err());
    }
}
