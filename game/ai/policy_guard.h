#pragma once

#include <filesystem>
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace game::ai {

enum class ChangeAction {
  Proposed,
  Applied,
  Reverted,
};

struct ResourceLimits {
  int max_cpu_percent{70};
  int max_ram_mb{4096};
  int max_time_seconds{900};
};

struct CircuitBreakerConfig {
  int max_failed_deployments{3};
  double max_regression_threshold{0.05};
  std::string emergency_disable_file{"logs/.autonomy_disabled"};
};

struct ExecutionPolicy {
  std::vector<std::string> writable_allow_prefixes;
  std::vector<std::string> writable_deny_prefixes;
  std::vector<std::string> allowed_domains;
  std::vector<int> allowed_ports;
  ResourceLimits limits;
  CircuitBreakerConfig circuit_breakers;
};

struct DeploymentDecision {
  bool allowed{false};
  std::string reason;
};

class PolicyGuard {
 public:
  PolicyGuard(std::filesystem::path policy_path,
              std::filesystem::path audit_log_path = "logs/autonomy_audit.log");

  bool ReloadPolicy();

  DeploymentDecision EnforceBeforePatchDeployment(
      const std::vector<std::filesystem::path>& touched_files,
      const std::optional<std::string>& outbound_domain,
      int outbound_port,
      int requested_cpu_percent,
      int requested_ram_mb,
      int requested_runtime_seconds,
      double regression_score) const;

  void RecordProposed(const std::string& change_id,
                      const std::string& summary) const;
  void RecordApplied(const std::string& change_id,
                     const std::string& summary,
                     bool success) const;
  void RecordReverted(const std::string& change_id,
                      const std::string& summary,
                      const std::string& reason) const;

 private:
  bool IsWritablePathAllowed(const std::filesystem::path& path,
                             std::string* reason) const;
  bool IsNetworkAllowed(const std::optional<std::string>& domain,
                        int port,
                        std::string* reason) const;
  bool AreResourcesAllowed(int cpu_percent,
                           int ram_mb,
                           int runtime_seconds,
                           std::string* reason) const;
  bool IsCircuitBreakerOpen(double regression_score, std::string* reason) const;

  void Audit(ChangeAction action,
             const std::string& change_id,
             const std::map<std::string, std::string>& fields) const;

  int CountRecentFailedDeployments() const;

  std::filesystem::path policy_path_;
  std::filesystem::path audit_log_path_;
  ExecutionPolicy policy_;
};

}  // namespace game::ai
