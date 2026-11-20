use std::borrow::Cow;
use time::{OffsetDateTime, UtcOffset, error::Format, format_description::well_known::Rfc3339};

pub(crate) fn format_utc(value: OffsetDateTime) -> Result<String, Format> {
    let mut text = value.to_offset(UtcOffset::UTC).format(&Rfc3339)?;
    // Keep the existing receipt/log layout: +00:00 and 0, 3, 6 or 9 fractional digits.
    text.pop();
    if let Some((_, fraction)) = text.rsplit_once('.') {
        text.push_str(&"00"[..(3 - fraction.len() % 3) % 3]);
    }
    text.push_str("+00:00");
    Ok(text)
}

// Keep the previous parser's accepted separators and sort by absolute time.
// A leap second uses the preceding epoch second with an extra billion nanos.
pub(crate) fn parse(value: &str) -> Option<(i64, u32)> {
    if !matches!(value.as_bytes().get(10), Some(b'T' | b't' | b' ')) {
        return None;
    }
    let leap = value.get(17..19) == Some("60");
    let mut input = Cow::Borrowed(value);
    if leap {
        input.to_mut().replace_range(17..19, "59");
    }
    // Older signed review records may use the Unicode minus in the offset.
    if let Some(index) = value.get(19..).and_then(|suffix| suffix.find('−')) {
        let start = 19 + index;
        input
            .to_mut()
            .replace_range(start..start + '−'.len_utf8(), "-");
    }
    let parsed = OffsetDateTime::parse(&input, &Rfc3339).ok()?;
    Some((
        parsed.unix_timestamp(),
        parsed.nanosecond() + if leap { 1_000_000_000 } else { 0 },
    ))
}

pub(crate) fn parse_micros(value: &str) -> Option<i64> {
    let (seconds, nanos) = parse(value)?;
    Some(seconds * 1_000_000 + i64::from(nanos / 1_000))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn utc_output_preserves_offset_and_fraction_width() {
        for (nanos, suffix) in [
            (0, "+00:00"),
            (120_000_000, ".120+00:00"),
            (123_450_000, ".123450+00:00"),
            (123_456_780, ".123456780+00:00"),
        ] {
            let timestamp = OffsetDateTime::from_unix_timestamp_nanos(nanos).unwrap();
            assert_eq!(
                format_utc(timestamp).unwrap(),
                format!("1970-01-01T00:00:00{suffix}")
            );
        }
    }

    #[test]
    fn retained_timestamps_preserve_utc_order_and_microseconds() {
        assert_eq!(
            parse("1969-12-31 23:59:59.9999999999z"),
            parse("1970-01-01T00:59:59.999999999+01:00")
        );
        assert_eq!(parse("1970-01-01T00:00:00−00:30"), Some((1800, 0)));
        assert_eq!(parse_micros("1969-12-31T23:59:59.999999999Z"), Some(-1));
        assert!(parse("2024-06-07X00:00:00Z").is_none());
        assert!(parse("2024-06-07T00:00:00+24:00").is_none());
        assert!(parse("2024-06-07T00:00:00Z trailing").is_none());
        let leap = "2016-12-31T23:59:60.5Z";
        assert!(parse("2016-12-31T23:59:59.999999999Z").unwrap() < parse(leap).unwrap());
        assert!(parse(leap).unwrap() < parse("2017-01-01T00:00:00Z").unwrap());
        assert_eq!(parse_micros(leap), parse_micros("2017-01-01T00:00:00.5Z"));
    }
}
