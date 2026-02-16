#include "game/ai/policy_guard.h"

#include <algorithm>
#include <chrono>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <sstream>

namespace game::ai {
namespace {

std::string Trim(const std::string& s) {
  const auto start = s.find_first_not_of(" \t\r\n");
  if (start == std::string::npos) {
    return "";
  }
  const auto end = s.find_last_not_of(" \t\r\n");
  return s.substr(start, end - start + 1);
}

bool StartsWith(const std::string& value, const std::string& prefix) {
  return value.size() >= prefix.size() &&
         value.compare(0, prefix.size(), prefix) == 0;
}

std::string ToIso8601Now() {
  const auto now = std::chrono::system_clock::now();
  const std::time_t now_c = std::chrono::system_clock::to_time_t(now);
  std::tm tm{};
#if defined(_WIN32)
  gmtime_s(&tm, &now_c);
#else
  gmtime_r(&now_c, &tm);
#endif
  std::ostringstream out;
  out << std::put_time(&tm, "%Y-%m-%dT%H:%M:%SZ");
  return out.str();
}

}  // namespace

PolicyGuard::PolicyGuard(std::filesystem::path policy_path,
                         std::filesystem::path audit_log_path)
    : policy_path_(std::move(policy_path)),
      audit_log_path_(std::move(audit_log_path)) {
  ReloadPolicy();
}

bool PolicyGuard::ReloadPolicy() {
  std::ifstream in(policy_path_);
  if (!in.is_open()) {
    return false;
  }

  policy_ = ExecutionPolicy{};

  enum class Context { None, AllowWritable, DenyWritable, AllowDomain, AllowPorts };

  Context context = Context::None;
  bool in_ai_writable = false;
  bool in_network_allow = false;

  std::string line;
  while (std::getline(in, line)) {
    const auto trimmed = Trim(line);
    if (trimmed.empty() || StartsWith(trimmed, "#")) {
      continue;
    }

    if (trimmed == "autonomy:" || trimmed == "network:" ||
        trimmed == "resource_limits:" || trimmed == "cpu:" ||
        trimmed == "memory:" || trimmed == "execution:" ||
        trimmed == "circuit_breakers:") {
      context = Context::None;
      in_ai_writable = false;
      if (trimmed != "network:") {
        in_network_allow = false;
      }
      continue;
    }

    if (trimmed == "ai_writable:") {
      in_ai_writable = true;
      context = Context::None;
      continue;
    }

    if (trimmed == "allow:") {
      if (in_ai_writable) {
        context = Context::AllowWritable;
      }
      if (!in_ai_writable) {
        in_network_allow = true;
      }
      continue;
    }

    if (trimmed == "deny:") {
      if (in_ai_writable) {
        context = Context::DenyWritable;
      }
      if (!in_ai_writable) {
        in_network_allow = false;
      }
      continue;
    }

    if (trimmed == "domains:") {
      context = in_network_allow ? Context::AllowDomain : Context::None;
      continue;
    }

    if (trimmed == "ports:") {
      context = in_network_allow ? Context::AllowPorts : Context::None;
      continue;
    }

    if (StartsWith(trimmed, "- ")) {
      const auto item = Trim(trimmed.substr(2));
      switch (context) {
        case Context::AllowWritable:
          policy_.writable_allow_prefixes.push_back(item);
          break;
        case Context::DenyWritable:
          policy_.writable_deny_prefixes.push_back(item);
          break;
        case Context::AllowDomain:
          if (!item.empty() && item != "\"*\"") {
            policy_.allowed_domains.push_back(item);
          }
          break;
        case Context::AllowPorts:
          policy_.allowed_ports.push_back(std::stoi(item));
          break;
        default:
          break;
      }
      continue;
    }

    if (StartsWith(trimmed, "max_percent:")) {
      policy_.limits.max_cpu_percent =
          std::stoi(Trim(trimmed.substr(std::string("max_percent:").size())));
    } else if (StartsWith(trimmed, "max_ram_mb:")) {
      policy_.limits.max_ram_mb =
          std::stoi(Trim(trimmed.substr(std::string("max_ram_mb:").size())));
    } else if (StartsWith(trimmed, "max_time_seconds:")) {
      policy_.limits.max_time_seconds =
          std::stoi(Trim(trimmed.substr(std::string("max_time_seconds:").size())));
    } else if (StartsWith(trimmed, "max_failed_deployments:")) {
      policy_.circuit_breakers.max_failed_deployments = std::stoi(
          Trim(trimmed.substr(std::string("max_failed_deployments:").size())));
    } else if (StartsWith(trimmed, "max_regression_threshold:")) {
      policy_.circuit_breakers.max_regression_threshold = std::stod(
          Trim(trimmed.substr(std::string("max_regression_threshold:").size())));
    } else if (StartsWith(trimmed, "emergency_disable_file:")) {
      policy_.circuit_breakers.emergency_disable_file =
          Trim(trimmed.substr(std::string("emergency_disable_file:").size()));
    }
  }

  if (policy_.writable_allow_prefixes.empty()) {
    policy_.writable_allow_prefixes = {"game/ai/", "policies/", "logs/", "tools/"};
  }

  return true;
}

DeploymentDecision PolicyGuard::EnforceBeforePatchDeployment(
    const std::vector<std::filesystem::path>& touched_files,
    const std::optional<std::string>& outbound_domain,
    int outbound_port,
    int requested_cpu_percent,
    int requested_ram_mb,
    int requested_runtime_seconds,
    double regression_score) const {
  std::string reason;
  for (const auto& path : touched_files) {
    if (!IsWritablePathAllowed(path, &reason)) {
      return {false, reason};
    }
  }

  if (!IsNetworkAllowed(outbound_domain, outbound_port, &reason)) {
    return {false, reason};
  }

  if (!AreResourcesAllowed(requested_cpu_percent, requested_ram_mb,
                           requested_runtime_seconds, &reason)) {
    return {false, reason};
  }

  if (IsCircuitBreakerOpen(regression_score, &reason)) {
    return {false, reason};
  }

  return {true, "allowed"};
}

void PolicyGuard::RecordProposed(const std::string& change_id,
                                 const std::string& summary) const {
  Audit(ChangeAction::Proposed, change_id, {{"summary", summary}});
}

void PolicyGuard::RecordApplied(const std::string& change_id,
                                const std::string& summary,
                                bool success) const {
  Audit(ChangeAction::Applied, change_id,
        {{"summary", summary}, {"success", success ? "true" : "false"}});
}

void PolicyGuard::RecordReverted(const std::string& change_id,
                                 const std::string& summary,
                                 const std::string& reason) const {
  Audit(ChangeAction::Reverted, change_id,
        {{"summary", summary}, {"reason", reason}});
}

bool PolicyGuard::IsWritablePathAllowed(const std::filesystem::path& path,
                                        std::string* reason) const {
  const auto path_str = path.generic_string();

  for (const auto& deny : policy_.writable_deny_prefixes) {
    if (StartsWith(path_str, deny)) {
      if (reason) {
        *reason = "write denied for path: " + path_str;
      }
      return false;
    }
  }

  for (const auto& allow : policy_.writable_allow_prefixes) {
    if (StartsWith(path_str, allow)) {
      return true;
    }
  }

  if (reason) {
    *reason = "write outside allowed scope: " + path_str;
  }
  return false;
}

bool PolicyGuard::IsNetworkAllowed(const std::optional<std::string>& domain,
                                   int port,
                                   std::string* reason) const {
  if (!domain.has_value()) {
    return true;
  }

  if (std::find(policy_.allowed_domains.begin(), policy_.allowed_domains.end(),
                domain.value()) == policy_.allowed_domains.end()) {
    if (reason) {
      *reason = "domain not allowed: " + domain.value();
    }
    return false;
  }

  if (std::find(policy_.allowed_ports.begin(), policy_.allowed_ports.end(), port) ==
      policy_.allowed_ports.end()) {
    if (reason) {
      *reason = "port not allowed: " + std::to_string(port);
    }
    return false;
  }

  return true;
}

bool PolicyGuard::AreResourcesAllowed(int cpu_percent,
                                      int ram_mb,
                                      int runtime_seconds,
                                      std::string* reason) const {
  if (cpu_percent > policy_.limits.max_cpu_percent) {
    if (reason) {
      *reason = "cpu request exceeds max policy";
    }
    return false;
  }

  if (ram_mb > policy_.limits.max_ram_mb) {
    if (reason) {
      *reason = "ram request exceeds max policy";
    }
    return false;
  }

  if (runtime_seconds > policy_.limits.max_time_seconds) {
    if (reason) {
      *reason = "runtime request exceeds max policy";
    }
    return false;
  }

  return true;
}

bool PolicyGuard::IsCircuitBreakerOpen(double regression_score,
                                       std::string* reason) const {
  if (!policy_.circuit_breakers.emergency_disable_file.empty() &&
      std::filesystem::exists(policy_.circuit_breakers.emergency_disable_file)) {
    if (reason) {
      *reason = "autonomy disabled by local emergency switch";
    }
    return true;
  }

  if (CountRecentFailedDeployments() >=
      policy_.circuit_breakers.max_failed_deployments) {
    if (reason) {
      *reason = "circuit breaker open: too many failed deployments";
    }
    return true;
  }

  if (regression_score > policy_.circuit_breakers.max_regression_threshold) {
    if (reason) {
      *reason = "circuit breaker open: regression threshold exceeded";
    }
    return true;
  }

  return false;
}

void PolicyGuard::Audit(ChangeAction action,
                        const std::string& change_id,
                        const std::map<std::string, std::string>& fields) const {
  std::filesystem::create_directories(audit_log_path_.parent_path());

  std::ofstream out(audit_log_path_, std::ios::app);
  if (!out.is_open()) {
    return;
  }

  std::string action_text;
  switch (action) {
    case ChangeAction::Proposed:
      action_text = "proposed";
      break;
    case ChangeAction::Applied:
      action_text = "applied";
      break;
    case ChangeAction::Reverted:
      action_text = "reverted";
      break;
  }

  out << "{\"timestamp\":\"" << ToIso8601Now() << "\",\"action\":\""
      << action_text << "\",\"change_id\":\"" << change_id << "\"";

  for (const auto& [key, value] : fields) {
    out << ",\"" << key << "\":\"" << value << "\"";
  }

  out << "}\n";
}

int PolicyGuard::CountRecentFailedDeployments() const {
  std::ifstream in(audit_log_path_);
  if (!in.is_open()) {
    return 0;
  }

  int failed = 0;
  std::string line;
  while (std::getline(in, line)) {
    if (line.find("\"action\":\"applied\"") != std::string::npos &&
        line.find("\"success\":\"false\"") != std::string::npos) {
      ++failed;
    }
  }

  return failed;
}

}  // namespace game::ai
