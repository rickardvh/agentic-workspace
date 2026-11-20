/** Optional YAML 1.2 renderer. Pass the namespace imported from yaml@2.9.1. */
type YamlLibrary = Pick<typeof import("yaml"), "Document" | "isMap" | "isSeq" | "parseDocument">;
export type SelectionRole = "detail" | "answer" | "action";
export interface AgentView {
  readonly yaml: string;
  /** Return the exact value represented by a handle in this response. */
  inspect(handle: string): string;
  /** Reject expired, unissued and wrong-role selections before dispatch. */
  resolve(handle: string, role: SelectionRole): string;
}
export function renderAgentYaml(raw: string, yamlLibrary: YamlLibrary): string;
export function createAgentSession(yamlLibrary: YamlLibrary): {
  present(raw: string): AgentView;
  clear(): void;
};
