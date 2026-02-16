#include "game/ai/audit_inspector.h"

#include <fstream>
#include <sstream>

namespace game::ai {
namespace {

std::string ExtractField(const std::string& line, const std::string& field) {
  const std::string key = "\"" + field + "\":\"";
  const auto start = line.find(key);
  if (start == std::string::npos) {
    return "";
  }

  const auto value_start = start + key.size();
  const auto value_end = line.find('"', value_start);
  if (value_end == std::string::npos) {
    return "";
  }

  return line.substr(value_start, value_end - value_start);
}

}  // namespace

AuditInspector::AuditInspector(std::filesystem::path audit_log_path)
    : audit_log_path_(std::move(audit_log_path)) {}

std::vector<AuditEntry> AuditInspector::RecentEntries(std::size_t limit) const {
  std::ifstream in(audit_log_path_);
  if (!in.is_open()) {
    return {};
  }

  std::vector<AuditEntry> all;
  std::string line;
  while (std::getline(in, line)) {
    AuditEntry entry;
    entry.timestamp = ExtractField(line, "timestamp");
    entry.action = ExtractField(line, "action");
    entry.change_id = ExtractField(line, "change_id");
    entry.summary = ExtractField(line, "summary");

    if (entry.action == "applied") {
      const auto success = ExtractField(line, "success");
      entry.outcome = success == "true" ? "success" : "failed";
    } else if (entry.action == "reverted") {
      entry.outcome = "reverted:" + ExtractField(line, "reason");
    }

    all.push_back(std::move(entry));
  }

  if (all.size() <= limit) {
    return all;
  }

  return {all.end() - static_cast<long>(limit), all.end()};
}

}  // namespace game::ai
