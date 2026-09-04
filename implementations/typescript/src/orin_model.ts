export type Diagnostic = {
  code: string;
  message: string;
  objectId?: string;
};

export class SemanticModel {
  document: Record<string, any>;

  constructor(document: Record<string, any>) {
    this.document = JSON.parse(JSON.stringify(document));
  }

  static fromJsonText(text: string): SemanticModel {
    return new SemanticModel(JSON.parse(text));
  }

  canonical(): Record<string, any> {
    const canonical = JSON.parse(JSON.stringify(this.document));
    delete canonical.implementationPolicies;
    if (canonical.module && typeof canonical.module === "object") {
      delete canonical.module.implementationPolicies;
    }
    this.removeMetadata(canonical);
    canonical.objects = (canonical.objects || []).slice().sort((a: any, b: any) => String(a.id).localeCompare(String(b.id)));
    return canonical;
  }

  diagnostics(): Diagnostic[] {
    const diagnostics: Diagnostic[] = [];
    for (const obj of this.document.objects || []) {
      if (
        obj &&
        obj.kind === "uncertainty" &&
        obj.consequential === true &&
        obj.status === "unresolved"
      ) {
        diagnostics.push({
          code: "ORIN-E041",
          message: `unresolved consequential uncertainty: ${obj.name || obj.id}`,
          objectId: obj.id,
        });
      }
    }
    return diagnostics;
  }

  compilationStatus(): "blocked" | "eligible" {
    return this.diagnostics().some((item) => item.code === "ORIN-E041") ? "blocked" : "eligible";
  }

  private removeMetadata(value: any): void {
    if (Array.isArray(value)) {
      for (const child of value) {
        this.removeMetadata(child);
      }
      return;
    }
    if (value && typeof value === "object") {
      delete value.source;
      delete value.provenance;
      for (const child of Object.values(value)) {
        this.removeMetadata(child);
      }
    }
  }
}
