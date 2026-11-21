// Generated from source_decision_contract.json. Regenerate with make render-schema-reference.
/** JSON transport declarations, not an executable owner or validation model. */
export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
export type JsonObject = { [key: string]: Json };
export type Projection = "compact" | "full" | "carried";
export interface WorkContext {
  target?: string;
  task?: string;
  changed?: string[];
  request?: Json;
  material?: JsonObject[];
  maintenance?: "configuration";
  projection?: Projection;
  delivered?: string[];
  reuse_delivery?: boolean;
  short_restrictions?: boolean;
  available_sources?: { reference: string; revision: string; extent: string; selector?: string; content_revision?: string }[];
}
export interface StartInput extends WorkContext {
  /** Native-carried read-only setup job selection; submit the returned input unchanged. */
  setup?: JsonObject;
  reference?: string;
  /** Read one exact repository-relative payload observation via the effective Configuration reference. */
  payload_path?: string;
  answer?: Json;
}
export interface InvokeInput extends WorkContext {
  invocation?: Json;
  reference?: string;
  /** Execute the exact current workspace.cli_invoke question with its reference. */
  answer?: "authorize-write";
}
/** Results retain the exact Rust shape, including unknown owner contributions. */
export function start(context: StartInput): JsonObject;
export function invoke(context: InvokeInput): JsonObject;
/** Resource request validation and operation variants are native-owned. */
export interface ResourceInput extends WorkContext {
  target: string;
  request: JsonObject;
}
export function resources(context: ResourceInput): JsonObject;
export function selectReference(context: WorkContext & Pick<StartInput, "payload_path">, reference: string, answer?: Json): JsonObject;
export function answerCarried(carriage: JsonObject, reference: string, answer: Json): JsonObject;
export function invokeCarried(carriage: JsonObject, reference: string): JsonObject;
