export type SelectionRole = "detail" | "answer" | "action";
export interface AgentView {
  readonly yaml: string;
  /** Return the exact value represented by a handle in this response. */
  inspect(handle: string): string;
  /** Reject expired, unissued and wrong-role selections before dispatch. */
  resolve(handle: string, role: SelectionRole): string;
}
export function renderAgentYaml(raw: string, legacyYamlLibrary?: unknown): string;
export function createAgentSession(legacyYamlLibrary?: unknown): {
  present(raw: string): AgentView;
  clear(): void;
};
