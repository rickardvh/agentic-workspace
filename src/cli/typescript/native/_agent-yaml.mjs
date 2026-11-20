import assert from 'node:assert/strict'

function requireNumericSupport() {
  if (typeof JSON.rawJSON !== 'function') throw new TypeError('The YAML view requires Node 22.12 or later')
}

export async function loadYaml() {
  requireNumericSupport()
  try {
    return await import('yaml')
  } catch (error) {
    if (error.code !== 'ERR_MODULE_NOT_FOUND') throw error
    throw new Error('Install yaml@2.9.1 alongside the AW npm package to enable YAML output.')
  }
}

// AW uses serde_json integers (including u64) and finite IEEE doubles. Keep
// integer lexemes exact instead of passing them through a JavaScript Number.
export function parseJSON(text) {
  if (typeof text !== 'string') throw new TypeError('Expected the original AW JSON text')
  requireNumericSupport()
  return JSON.parse(text, (_key, value, context) => {
    if (typeof value !== 'number') return value
    if (!Number.isFinite(value)) throw new RangeError('Number outside AW numeric range')
    if (/^-?\d+$/.test(context.source) && context.source !== '-0') {
      return BigInt(context.source)
    }
    return value
  })
}

export function jsonText(value) {
  return JSON.stringify(value, (_key, item) => {
    if (typeof item === 'bigint') return JSON.rawJSON(String(item))
    if (Object.is(item, -0)) return JSON.rawJSON('-0.0')
    if (typeof item === 'number' && Number.isInteger(item)) {
      const decimal = String(item)
      return JSON.rawJSON(decimal.includes('e') ? decimal : decimal + '.0')
    }
    return item
  })
}

function anchorName(index) {
  let name = ''
  for (let n = index; n > 0; n = Math.floor((n - 1) / 26)) {
    name = String.fromCharCode(97 + (n - 1) % 26) + name
  }
  return name
}

const blockStyle = { lineWidth: 0, indent: 1, indentSeq: false, flowCollectionPadding: false }
const quoteControls = /[\u007f-\u009f\u2028\u2029\ufeff\ufffe\uffff]/
const escapeControls = new RegExp(quoteControls.source, 'g')

function safeStrings(tags) {
  return tags.map(tag => tag.tag === 'tag:yaml.org,2002:str' ? {
    ...tag,
    stringify(node, ...context) {
      if (!quoteControls.test(node.value)) return tag.stringify(node, ...context)
      return JSON.stringify(node.value).replace(escapeControls, character =>
        '\\u' + character.charCodeAt(0).toString(16).padStart(4, '0'))
    }
  } : tag)
}

export function anchored(value, yamlLibrary, options = {}, useAnchors = true) {
  const { Document, isMap, isSeq, parseDocument } = yamlLibrary
  const { minLength = 24, name = anchorName, inlineLists = true, style = blockStyle } = options
  const doc = new Document(value, { aliasDuplicateObjects: false, customTags: safeStrings })
  const first = new Map()
  let anchorCount = 0
  function visit(node, item) {
    const key = useAnchors ? jsonText(item) : ''
    if (key.length >= minLength) {
      const existing = first.get(key)
      if (existing) {
        if (!existing.anchor) {
          anchorCount += 1
          existing.anchor = name(anchorCount)
        }
        return doc.createAlias(existing)
      }
      first.set(key, node)
    }
    if (isMap(node)) {
      for (const entry of node.items) entry.value = visit(entry.value, item[entry.key.value])
    } else if (isSeq(node)) {
      if (inlineLists && item.length <= 12 && jsonText(item).length <= 200 &&
          item.every(x => x === null || typeof x !== 'object')) node.flow = true
      node.items = node.items.map((child, i) => visit(child, item[i]))
    } else if (typeof item === 'number') {
      // BigInts represent JSON integers. A Number came from a floating-point
      // value, even when its shortest decimal has no fractional digit.
      if (String(item).includes('e')) node.tag = 'tag:yaml.org,2002:float'
      else node.minFractionDigits = 1
    }
    return node
  }
  doc.contents = visit(doc.contents, value)
  const yaml = doc.toString(style)
  const parsed = parseDocument(yaml, { intAsBigInt: true })
  if (parsed.errors.length) throw parsed.errors[0]
  // A valid input may contain enough repeated nested records to trip the
  // default alias-expansion limit. Keep that limit intact for readers.
  let expanded
  try {
    expanded = parsed.toJS()
  } catch (error) {
    if (useAnchors && error instanceof ReferenceError && error.message.includes('Excessive alias count')) {
      return anchored(value, yamlLibrary, options, false)
    }
    throw error
  }
  assert.ok(jsonText(expanded) === jsonText(value), 'Lossy YAML rendering')
  return yaml
}
