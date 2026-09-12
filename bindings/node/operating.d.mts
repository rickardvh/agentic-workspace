/** JSON transport declarations, not an executable owner or validation model. */
export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
export type JsonObject = { [key: string]: Json };
export type Projection = "compact" | "full" | "carried";
export interface WorkContext {
  target?: string;
  task?: string;
  changed?: string[];
  request?: Json;
  projection?: Projection;
  delivered?: string[];
}
export interface StartInput extends WorkContext {
  reference?: string;
  answer?: Json;
}
export interface InvokeInput extends WorkContext {
  invocation?: Json;
  reference?: string;
}
/** Results retain the exact Rust shape, including unknown owner contributions. */
export function start(context: StartInput): JsonObject;
export function invoke(context: InvokeInput): JsonObject;
export interface ResourceInput {
  target: string;
  task?: string;
  changed?: string[];
  request: {
    operation: "audit" | "scratch-create" | "scratch-remove" | "scratch-retain" | "scratch-release" | "worktree-create" | "worktree-remove";
    path?: string;
    base?: string;
    need?: "conflicting-checkout" | "transport-requires-isolation" | "destructive-validation";
    reason?: string;
    policy_revision?: string;
    policy_answer?: "permits-isolation";
    expected_revision?: string;
    disposable_outputs?: ("target" | ".pytest_cache" | ".venv")[];
  };
}
export function resources(context: ResourceInput): JsonObject;
export function selectReference(context: WorkContext, reference: string, answer?: Json): JsonObject;
export function answerCarried(carriage: JsonObject, reference: string, answer: Json): JsonObject;
export function invokeCarried(carriage: JsonObject, reference: string): JsonObject;
