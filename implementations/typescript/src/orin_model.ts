export type Diagnostic = {
  code: string;
  message: string;
  objectId?: string;
};

export type ReadinessDiagnostic = {
  code: string;
  category: "required-decision" | "optional-default" | "unresolved-assumption" | "implementation-preference";
  message: string;
  severity: "blocked" | "warning" | "info";
  blocking: boolean;
  objectId?: string;
  path?: string;
  impactAreas: string[];
  affectedObjectPaths: string[];
};

export type ReadinessReport = {
  schemaVersion: string;
  status: "blocked" | "fail" | "eligible";
  validationStatus: "blocked" | "fail" | "eligible";
  summary: {
    blockingCount: number;
    nonBlockingCount: number;
    requiredDecisionCount: number;
    optionalDefaultCount: number;
    unresolvedAssumptionCount: number;
    implementationPreferenceCount: number;
  };
  diagnostics: ReadinessDiagnostic[];
};

const READINESS_DRIVER_KINDS = new Set(["workflow", "rule", "example"]);
const REFERENCE_FIELDS = ["affects", "constrainedBy", "demonstrates", "requires", "uses", "verifies"];
const COMPLETENESS_SCHEMA_VERSION = "0.1.0";
const READINESS_CATEGORY_ORDER = new Map([
  ["required-decision", 0],
  ["optional-default", 1],
  ["unresolved-assumption", 2],
  ["implementation-preference", 3],
]);
const READINESS_REQUIRED_FIELDS = new Map<string, Array<{ code: string; field: string; message: string; impactAreas: string[] }>>([
  ["capability", [
    { code: "ORIN-R001", field: "owner", message: "capability requires issuing authority/owner decision", impactAreas: ["safety"] },
    { code: "ORIN-R002", field: "scope", message: "capability requires scope decision", impactAreas: ["safety", "privacy"] },
  ]],
  ["effect", [
    { code: "ORIN-R010", field: "failureModes", message: "effect requires declared failure modes", impactAreas: ["operability"] },
    { code: "ORIN-R011", field: "dataAccess", message: "effect requires declared data access boundary", impactAreas: ["privacy", "safety"] },
  ]],
  ["workflow", [
    { code: "ORIN-R020", field: "failureBehavior", message: "workflow requires declared failure behavior", impactAreas: ["operability", "safety"] },
    { code: "ORIN-R021", field: "recoveryBehavior", message: "workflow requires declared recovery behavior", impactAreas: ["operability"] },
  ]],
]);
const READINESS_OPTIONAL_DEFAULTS = new Map<string, Array<{ code: string; field: string; defaultValue: string; message: string; impactAreas: string[] }>>([
  ["relation", [
    { code: "ORIN-R101", field: "deletionBehavior", defaultValue: "retain", message: "relation deletion behavior is unset; default retain is available", impactAreas: ["operability"] },
  ]],
  ["effect", [
    { code: "ORIN-R102", field: "retryPolicy", defaultValue: "none", message: "effect retry policy is unset; default none is available", impactAreas: ["cost", "operability"] },
  ]],
]);
const IMPLEMENTATION_PREFERENCE_AREAS = new Map<string, string[]>([
  ["optimize-for", ["cost", "operability"]],
  ["prefer", ["cost", "operability"]],
  ["require", ["operability"]],
  ["deploy-to", ["operability"]],
]);

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
    const objects = Array.isArray(this.document.objects) ? this.document.objects : [];
    const kinds = new Map<string, string>();
    const objectsById = new Map<string, Record<string, any>>();
    const hasStatefulWorkflow = objects.some(
      (obj) =>
        obj &&
        typeof obj === "object" &&
        obj.kind === "workflow" &&
        Array.isArray(obj.transitions) &&
        obj.transitions.length > 0,
    );

    for (const obj of objects) {
      if (obj && typeof obj.id === "string" && typeof obj.kind === "string") {
        kinds.set(obj.id, obj.kind);
        objectsById.set(obj.id, obj);
      }
    }
    const readinessReferences = this.collectReadinessReferences(objects, kinds, objectsById);
    const relationReferences = this.collectReadinessRelationReferences(objects, kinds);

    for (const obj of objects) {
      if (!obj || typeof obj !== "object") {
        continue;
      }
      if (
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
      if (obj.kind === "effect") {
        const effectName = typeof obj.name === "string" ? obj.name : "";
        if (effectName.startsWith("persistent-entity-store.")) {
          const durability = obj.durability;
          if (durability === undefined || durability === null) {
            diagnostics.push({
              code: "ORIN-E039",
              message: "persistence effect requires durability contract",
              objectId: obj.id,
            });
          } else if (durability !== "strong" && durability !== "eventual") {
            diagnostics.push({
              code: "ORIN-E040",
              message: `invalid durability contract: ${durability}`,
              objectId: obj.id,
            });
          }
        }
      }
      if (obj.kind === "workflow") {
        this.validateWorkflow(obj, kinds, objectsById, diagnostics);
      }
    }
    for (const obj of objects) {
      if (!obj || typeof obj !== "object" || obj.kind !== "effect") {
        continue;
      }
      if (typeof obj.id === "string" && !readinessReferences.has(obj.id)) {
        diagnostics.push({
          code: "ORIN-E042",
          message: "effect declaration is not referenced by any workflow/rule/example",
          objectId: obj.id,
        });
      }
    }
    for (const obj of objects) {
      if (!obj || typeof obj !== "object" || obj.kind !== "capability") {
        continue;
      }
      if (typeof obj.id === "string" && !readinessReferences.has(obj.id)) {
        diagnostics.push({
          code: "ORIN-E043",
          message: "capability declaration is not referenced by any workflow/rule/example",
          objectId: obj.id,
        });
      }
    }
    if (hasStatefulWorkflow) {
      for (const obj of objects) {
        if (!obj || typeof obj !== "object" || obj.kind !== "state") {
          continue;
        }
        if (typeof obj.id === "string" && !readinessReferences.has(obj.id)) {
          diagnostics.push({
            code: "ORIN-E044",
            message: "state declaration is not referenced by any workflow/rule/example",
            objectId: obj.id,
          });
        }
      }
    }
    if (relationReferences.size > 0) {
      for (const obj of objects) {
        if (!obj || typeof obj !== "object" || obj.kind !== "relation") {
          continue;
        }
        if (typeof obj.id === "string" && !relationReferences.has(obj.id)) {
          diagnostics.push({
            code: "ORIN-E045",
            message: "relation declaration is not referenced by any workflow/rule/example",
            objectId: obj.id,
          });
        }
      }
    }
    diagnostics.push(...this.collectRuleContradictionDiagnostics(objects));
    return diagnostics;
  }

  compilationStatus(): "blocked" | "fail" | "eligible" {
    const diagnostics = this.diagnostics();
    if (diagnostics.some((item) => item.code === "ORIN-E041")) {
      return "blocked";
    }
    return diagnostics.length > 0 ? "fail" : "eligible";
  }

  readinessReport(): ReadinessReport {
    if (!Array.isArray(this.document.objects)) {
      return {
        schemaVersion: COMPLETENESS_SCHEMA_VERSION,
        status: "fail",
        validationStatus: "fail",
        summary: {
          blockingCount: 1,
          nonBlockingCount: 0,
          requiredDecisionCount: 1,
          optionalDefaultCount: 0,
          unresolvedAssumptionCount: 0,
          implementationPreferenceCount: 0,
        },
        diagnostics: [{
          code: "ORIN-R900",
          category: "required-decision",
          message: "semantic model structure is invalid; fix validation errors before readiness analysis",
          severity: "blocked",
          blocking: true,
          path: "/objects",
          impactAreas: [],
          affectedObjectPaths: [],
        }],
      };
    }

    const objects = this.document.objects as Array<Record<string, any>>;
    const reverseReferences = this.buildReverseReferenceGraph(objects);
    const readinessDiagnostics: ReadinessDiagnostic[] = [];
    for (const obj of objects) {
      if (!obj || typeof obj !== "object") {
        continue;
      }
      readinessDiagnostics.push(...this.collectRequiredFieldReadiness(obj, reverseReferences));
      readinessDiagnostics.push(...this.collectOptionalDefaultReadiness(obj, reverseReferences));
      if (obj.kind === "uncertainty" && obj.status === "unresolved") {
        readinessDiagnostics.push(this.collectUncertaintyReadiness(obj, reverseReferences));
      }
    }
    readinessDiagnostics.push(...this.collectImplementationPreferenceReadiness());
    readinessDiagnostics.sort((left, right) =>
      (READINESS_CATEGORY_ORDER.get(left.category) ?? 99) - (READINESS_CATEGORY_ORDER.get(right.category) ?? 99)
      || left.code.localeCompare(right.code)
      || (left.path ?? "").localeCompare(right.path ?? "")
      || (left.objectId ?? "").localeCompare(right.objectId ?? "")
      || left.message.localeCompare(right.message),
    );

    const validationStatus = this.compilationStatus();
    const status = validationStatus === "fail"
      ? "fail"
      : (validationStatus === "blocked" || readinessDiagnostics.some((diagnostic) => diagnostic.blocking))
        ? "blocked"
        : "eligible";
    return {
      schemaVersion: COMPLETENESS_SCHEMA_VERSION,
      status,
      validationStatus,
      summary: {
        blockingCount: readinessDiagnostics.filter((diagnostic) => diagnostic.blocking).length,
        nonBlockingCount: readinessDiagnostics.filter((diagnostic) => !diagnostic.blocking).length,
        requiredDecisionCount: readinessDiagnostics.filter((diagnostic) => diagnostic.category === "required-decision").length,
        optionalDefaultCount: readinessDiagnostics.filter((diagnostic) => diagnostic.category === "optional-default").length,
        unresolvedAssumptionCount: readinessDiagnostics.filter((diagnostic) => diagnostic.category === "unresolved-assumption").length,
        implementationPreferenceCount: readinessDiagnostics.filter((diagnostic) => diagnostic.category === "implementation-preference").length,
      },
      diagnostics: readinessDiagnostics,
    };
  }

  private validateWorkflow(
    workflow: Record<string, any>,
    kinds: Map<string, string>,
    objectsById: Map<string, Record<string, any>>,
    diagnostics: Diagnostic[],
  ): void {
    const requiredCapabilities = new Set<string>(
      Array.isArray(workflow.requires) ? workflow.requires.filter((item: unknown) => typeof item === "string") : [],
    );
    const usedEffects = Array.isArray(workflow.uses) ? workflow.uses.filter((item: unknown) => typeof item === "string") : [];
    for (const effectId of usedEffects) {
      const effect = objectsById.get(effectId);
      if (effect && Array.isArray(effect.requires)) {
        for (const capability of effect.requires) {
          if (typeof capability === "string") {
            requiredCapabilities.add(capability);
          }
        }
      }
    }

    const actor = workflow.actor;
    const hasActorCapabilities = Object.prototype.hasOwnProperty.call(workflow, "actorCapabilities");
    const rawBindings = workflow.actorCapabilities ?? [];
    const bindings = Array.isArray(rawBindings) ? rawBindings : [];
    if (!Array.isArray(rawBindings)) {
      diagnostics.push({
        code: "ORIN-E038",
        message: "workflow actorCapabilities must be a list",
        objectId: workflow.id,
      });
    }

    const validBindings: Array<{ actor: string; capability: string }> = [];
    for (const binding of bindings) {
      if (!binding || typeof binding !== "object") {
        diagnostics.push({
          code: "ORIN-E038",
          message: "workflow actorCapabilities entries must be objects",
          objectId: workflow.id,
        });
        continue;
      }
      const bindingActor = binding.actor;
      const bindingCapability = binding.capability;
      if (typeof bindingActor !== "string" || typeof bindingCapability !== "string") {
        diagnostics.push({
          code: "ORIN-E038",
          message: "workflow actorCapabilities entries require actor and capability strings",
          objectId: workflow.id,
        });
        continue;
      }
      validBindings.push({ actor: bindingActor, capability: bindingCapability });
    }

    if (actor === undefined || actor === null) {
      if (hasActorCapabilities) {
        diagnostics.push({
          code: "ORIN-E038",
          message: "workflow actorCapabilities require actor declaration",
          objectId: workflow.id,
        });
      }
      return;
    }
    if (typeof actor !== "string") {
      diagnostics.push({
        code: "ORIN-E038",
        message: "workflow actor must be a string input name",
        objectId: workflow.id,
      });
      return;
    }
    if (requiredCapabilities.size > 0 && !hasActorCapabilities) {
      diagnostics.push({
        code: "ORIN-E038",
        message: "workflow actor requires actorCapabilities contract for required capabilities/effects",
        objectId: workflow.id,
      });
    }

    const inputs = Array.isArray(workflow.inputs) ? workflow.inputs : [];
    const actorInput = inputs.find((value) => value && typeof value === "object" && value.name === actor);
    if (!actorInput) {
      diagnostics.push({
        code: "ORIN-E038",
        message: `workflow actor must reference a declared input: ${actor}`,
        objectId: workflow.id,
      });
      return;
    }
    if (kinds.get(actorInput.type) !== "entity-type") {
      diagnostics.push({
        code: "ORIN-E038",
        message: `workflow actor input must reference an entity-type: ${actor}`,
        objectId: workflow.id,
      });
      return;
    }

    const actorBindings: Array<{ actor: string; capability: string }> = [];
    for (const binding of validBindings) {
      if (binding.actor !== actor) {
        diagnostics.push({
          code: "ORIN-E038",
          message: `workflow actorCapabilities actor must match workflow actor: ${binding.actor}`,
          objectId: workflow.id,
        });
        continue;
      }
      actorBindings.push(binding);
    }
    if (!hasActorCapabilities) {
      return;
    }
    const boundCapabilities = new Set(actorBindings.map((binding) => binding.capability));
    const missing = [...requiredCapabilities].filter((capability) => !boundCapabilities.has(capability)).sort();
    if (missing.length > 0) {
      diagnostics.push({
        code: "ORIN-E037",
        message: `workflow actor is not bound to required capabilities: ${missing.join(", ")}`,
        objectId: workflow.id,
      });
    }
  }

  private collectReadinessReferences(
    objects: Array<Record<string, any>>,
    kinds: Map<string, string>,
    objectsById: Map<string, Record<string, any>>,
  ): Set<string> {
    const readinessReferences = new Set<string>();
    const readinessEffects = new Set<string>();
    for (const obj of objects) {
      if (!obj || typeof obj !== "object" || !READINESS_DRIVER_KINDS.has(obj.kind)) {
        continue;
      }
      for (const field of REFERENCE_FIELDS) {
        const values = obj[field];
        if (!Array.isArray(values)) {
          continue;
        }
        for (const value of values) {
          if (typeof value !== "string") {
            continue;
          }
          readinessReferences.add(value);
          if (kinds.get(value) === "effect") {
            readinessEffects.add(value);
          }
        }
      }
      if (obj.kind === "workflow") {
        const transitions = Array.isArray(obj.transitions) ? obj.transitions : [];
        for (const transition of transitions) {
          if (!transition || typeof transition !== "object") {
            continue;
          }
          if (typeof transition.from === "string") {
            readinessReferences.add(transition.from);
          }
          if (typeof transition.to === "string") {
            readinessReferences.add(transition.to);
          }
        }
        const actorCapabilities = Array.isArray(obj.actorCapabilities) ? obj.actorCapabilities : [];
        for (const binding of actorCapabilities) {
          if (binding && typeof binding === "object" && typeof binding.capability === "string") {
            readinessReferences.add(binding.capability);
          }
        }
      }
    }
    for (const effectId of readinessEffects) {
      const effect = objectsById.get(effectId);
      const requiredCapabilities = effect?.requires;
      if (!Array.isArray(requiredCapabilities)) {
        continue;
      }
      for (const capabilityId of requiredCapabilities) {
        if (typeof capabilityId === "string") {
          readinessReferences.add(capabilityId);
        }
      }
    }
    return readinessReferences;
  }

  private collectReadinessRelationReferences(
    objects: Array<Record<string, any>>,
    kinds: Map<string, string>,
  ): Set<string> {
    const relationReferences = new Set<string>();
    for (const obj of objects) {
      if (!obj || typeof obj !== "object" || !READINESS_DRIVER_KINDS.has(obj.kind)) {
        continue;
      }
      for (const field of REFERENCE_FIELDS) {
        const values = obj[field];
        if (!Array.isArray(values)) {
          continue;
        }
        for (const value of values) {
          if (typeof value === "string" && kinds.get(value) === "relation") {
            relationReferences.add(value);
          }
        }
      }
    }
    return relationReferences;
  }

  private collectRuleContradictionDiagnostics(objects: Array<Record<string, any>>): Diagnostic[] {
    const diagnostics: Diagnostic[] = [];
    for (const obj of objects) {
      if (!obj || typeof obj !== "object" || obj.kind !== "rule" || typeof obj.id !== "string") {
        continue;
      }
      const claims = Array.isArray(obj.claims) ? obj.claims : [];
      const claimPolarity = new Map<string, Set<boolean>>();
      for (const claim of claims) {
        const normalized = this.normalizeRuleClaim(claim);
        if (!normalized) {
          continue;
        }
        const polarities = claimPolarity.get(normalized.proposition) ?? new Set<boolean>();
        polarities.add(normalized.negative);
        claimPolarity.set(normalized.proposition, polarities);
      }
      const contradictory = [...claimPolarity.entries()]
        .filter(([, polarities]) => polarities.size > 1)
        .map(([proposition]) => proposition)
        .sort();
      for (const proposition of contradictory) {
        diagnostics.push({
          code: "ORIN-E046",
          message: `rule contains contradictory claims: ${proposition}`,
          objectId: obj.id,
        });
      }
    }
    return diagnostics;
  }

  private normalizeRuleClaim(claim: unknown): { negative: boolean; proposition: string } | null {
    let text: string;
    let negative = false;
    if (typeof claim === "string") {
      text = claim;
    } else if (claim && typeof claim === "object") {
      const claimText = (claim as Record<string, unknown>).text;
      if (typeof claimText !== "string") {
        return null;
      }
      text = claimText;
      negative = (claim as Record<string, unknown>).negated === true;
    } else {
      return null;
    }

    let normalized = text.toLowerCase().trim();
    if (!normalized) {
      return null;
    }
    if (normalized.startsWith("not ")) {
      negative = true;
      normalized = normalized.slice(4).trim();
    }
    normalized = normalized.replace(/[.,;:!?]+$/g, "").replace(/\s+/g, " ").trim();
    if (!normalized) {
      return null;
    }
    return { negative, proposition: normalized };
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

  private hasDeclaredValue(value: unknown): boolean {
    if (value === null || value === undefined) {
      return false;
    }
    if (typeof value === "string") {
      return value.trim().length > 0;
    }
    if (Array.isArray(value)) {
      return value.length > 0;
    }
    if (typeof value === "object") {
      return Object.keys(value as Record<string, unknown>).length > 0;
    }
    return true;
  }

  private escapePointerSegment(segment: string): string {
    return segment.replaceAll("~", "~0").replaceAll("/", "~1");
  }

  private objectPath(objectId: string, ...segments: string[]): string {
    return ["/objects", this.escapePointerSegment(objectId), ...segments.map((segment) => this.escapePointerSegment(segment))].join("/");
  }

  private modulePath(...segments: string[]): string {
    return ["/module", ...segments.map((segment) => this.escapePointerSegment(segment))].join("/");
  }

  private impactAreas(value: unknown, fallback: string[]): string[] {
    if (!Array.isArray(value)) {
      return [...fallback];
    }
    const normalized = [...new Set(value.filter((item): item is string => typeof item === "string" && item.trim().length > 0).map((item) => item.trim()))].sort();
    return normalized.length > 0 ? normalized : [...fallback];
  }

  private buildReverseReferenceGraph(objects: Array<Record<string, any>>): Map<string, Set<string>> {
    const reverseReferences = new Map<string, Set<string>>();
    const addReference = (targetId: string, sourceId: string) => {
      const existing = reverseReferences.get(targetId) ?? new Set<string>();
      existing.add(sourceId);
      reverseReferences.set(targetId, existing);
    };
    for (const obj of objects) {
      if (!obj || typeof obj.id !== "string") {
        continue;
      }
      for (const field of REFERENCE_FIELDS) {
        const values = obj[field];
        if (!Array.isArray(values)) {
          continue;
        }
        for (const targetId of values) {
          if (typeof targetId === "string") {
            addReference(targetId, obj.id);
          }
        }
      }
      if (obj.kind === "workflow") {
        const transitions = Array.isArray(obj.transitions) ? obj.transitions : [];
        for (const transition of transitions) {
          if (!transition || typeof transition !== "object") {
            continue;
          }
          if (typeof transition.from === "string") {
            addReference(transition.from, obj.id);
          }
          if (typeof transition.to === "string") {
            addReference(transition.to, obj.id);
          }
        }
        const bindings = Array.isArray(obj.actorCapabilities) ? obj.actorCapabilities : [];
        for (const binding of bindings) {
          if (binding && typeof binding === "object" && typeof binding.capability === "string") {
            addReference(binding.capability, obj.id);
          }
        }
      }
    }
    return reverseReferences;
  }

  private collectAffectedObjectPaths(seedIds: Set<string>, reverseReferences: Map<string, Set<string>>): string[] {
    const queue = [...seedIds].sort();
    let index = 0;
    const seen = new Set<string>();
    const paths: string[] = [];
    while (index < queue.length) {
      const current = queue[index]!;
      index += 1;
      if (seen.has(current)) {
        continue;
      }
      seen.add(current);
      paths.push(this.objectPath(current));
      for (const dependentId of [...(reverseReferences.get(current) ?? new Set<string>())].sort()) {
        if (!seen.has(dependentId)) {
          queue.push(dependentId);
        }
      }
    }
    return paths;
  }

  private collectRequiredFieldReadiness(
    obj: Record<string, any>,
    reverseReferences: Map<string, Set<string>>,
  ): ReadinessDiagnostic[] {
    if (typeof obj.id !== "string" || typeof obj.kind !== "string") {
      return [];
    }
    return (READINESS_REQUIRED_FIELDS.get(obj.kind) ?? [])
      .filter((rule) => !this.hasDeclaredValue(obj[rule.field]))
      .map((rule) => ({
        code: rule.code,
        category: "required-decision",
        message: rule.message,
        severity: "blocked",
        blocking: true,
        objectId: obj.id,
        path: this.objectPath(obj.id, rule.field),
        impactAreas: this.impactAreas(obj.impactAreas, rule.impactAreas),
        affectedObjectPaths: this.collectAffectedObjectPaths(new Set([obj.id]), reverseReferences),
      }));
  }

  private collectOptionalDefaultReadiness(
    obj: Record<string, any>,
    reverseReferences: Map<string, Set<string>>,
  ): ReadinessDiagnostic[] {
    if (typeof obj.id !== "string" || typeof obj.kind !== "string") {
      return [];
    }
    return (READINESS_OPTIONAL_DEFAULTS.get(obj.kind) ?? [])
      .filter((rule) => !this.hasDeclaredValue(obj[rule.field]))
      .map((rule) => ({
        code: rule.code,
        category: "optional-default",
        message: `${rule.message} (${rule.field}=${rule.defaultValue})`,
        severity: "info",
        blocking: false,
        objectId: obj.id,
        path: this.objectPath(obj.id, rule.field),
        impactAreas: [...rule.impactAreas],
        affectedObjectPaths: this.collectAffectedObjectPaths(new Set([obj.id]), reverseReferences),
      }));
  }

  private collectUncertaintyReadiness(
    obj: Record<string, any>,
    reverseReferences: Map<string, Set<string>>,
  ): ReadinessDiagnostic {
    const affectedIds = new Set<string>(typeof obj.id === "string" ? [obj.id] : []);
    for (const targetId of Array.isArray(obj.affects) ? obj.affects : []) {
      if (typeof targetId === "string") {
        affectedIds.add(targetId);
      }
    }
    const blocking = obj.consequential === true;
    const fallback = blocking ? ["cost", "operability", "privacy", "safety"] : ["cost", "operability"];
    const question = typeof obj.question === "string" ? obj.question : (typeof obj.name === "string" ? obj.name : "unresolved assumption");
    return {
      code: "ORIN-R201",
      category: "unresolved-assumption",
      message: `uncertainty remains unresolved: ${question}`,
      severity: blocking ? "blocked" : "warning",
      blocking,
      objectId: typeof obj.id === "string" ? obj.id : undefined,
      path: typeof obj.id === "string" ? this.objectPath(obj.id) : undefined,
      impactAreas: this.impactAreas(obj.impactAreas, fallback),
      affectedObjectPaths: this.collectAffectedObjectPaths(affectedIds, reverseReferences),
    };
  }

  private collectImplementationPreferenceReadiness(): ReadinessDiagnostic[] {
    const diagnostics: ReadinessDiagnostic[] = [];
    const modulePolicies = this.document.module && typeof this.document.module === "object" && this.document.module.implementationPolicies && typeof this.document.module.implementationPolicies === "object"
      ? this.document.module.implementationPolicies
      : {};
    for (const [key, value] of Object.entries(modulePolicies).sort(([left], [right]) => left.localeCompare(right))) {
      diagnostics.push({
        code: "ORIN-R301",
        category: "implementation-preference",
        message: `implementation preference selected: ${key}=${value}`,
        severity: "info",
        blocking: false,
        path: this.modulePath("implementationPolicies", key),
        impactAreas: [...(IMPLEMENTATION_PREFERENCE_AREAS.get(key) ?? ["operability"])],
        affectedObjectPaths: ["/module"],
      });
    }
    const rootPolicies = this.document.implementationPolicies && typeof this.document.implementationPolicies === "object"
      ? this.document.implementationPolicies
      : {};
    for (const [key, value] of Object.entries(rootPolicies).sort(([left], [right]) => left.localeCompare(right))) {
      diagnostics.push({
        code: "ORIN-R301",
        category: "implementation-preference",
        message: `implementation preference selected: ${key}=${value}`,
        severity: "info",
        blocking: false,
        path: `/implementationPolicies/${this.escapePointerSegment(key)}`,
        impactAreas: [...(IMPLEMENTATION_PREFERENCE_AREAS.get(key) ?? ["operability"])],
        affectedObjectPaths: ["/implementationPolicies"],
      });
    }
    return diagnostics;
  }
}
