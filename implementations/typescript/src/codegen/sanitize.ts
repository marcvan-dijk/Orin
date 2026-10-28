import { SemanticModel } from "../orin_model.ts";

export class GenerationRefused extends Error {}

// Reduces a model-derived identifier to a charset that is inert in any emitted comment or literal.
export function sanitizeId(value: unknown): string {
  return String(value).replace(/[^A-Za-z0-9._/-]/g, "_").slice(0, 200);
}

// Returns a safe module id, or refuses a model that is structurally malformed.
export function checkedModuleId(model: SemanticModel): string {
  const doc = model?.document;
  const module = doc?.module;
  if (!module || typeof module !== "object" || Array.isArray(module) || typeof module.id !== "string" || !module.id) {
    throw new GenerationRefused("malformed model: 'module.id' must be a non-empty string");
  }
  if (doc.objects !== undefined && !Array.isArray(doc.objects)) {
    throw new GenerationRefused("malformed model: 'objects' must be a list");
  }
  if (Array.isArray(doc.objects) && doc.objects.some((o: unknown) => !o || typeof o !== "object" || Array.isArray(o))) {
    throw new GenerationRefused("malformed model: every entry of 'objects' must be an object");
  }
  if (doc.unresolved !== undefined && !Array.isArray(doc.unresolved)) {
    throw new GenerationRefused("malformed model: 'unresolved' must be a list");
  }
  return sanitizeId(module.id);
}

export function readiness(model: SemanticModel) {
  try {
    return model.computeReadinessGates();
  } catch (error) {
    throw new GenerationRefused(`malformed model: ${error instanceof Error ? error.message : String(error)}`);
  }
}
