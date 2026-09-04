import { SemanticModel } from "./orin_model";

export function lower(model: SemanticModel): Record<string, any> {
  const moduleSection = model.document.module || {};
  const policies = moduleSection.implementationPolicies || model.document.implementationPolicies || {};
  return {
    behavior: model.canonical(),
    artifact: {
      latency: policies["optimize-for"] === "low-latency",
      managedServices: policies.prefer === "managed-services",
      persistence: policies.require || "relational-persistence",
      deployment: policies["deploy-to"] || "portable-infrastructure",
    },
  };
}
