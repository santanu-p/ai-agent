#pragma once

#include <filesystem>
#include <string>
#include <vector>

namespace game::ai {

struct AuditEntry {
  std::string timestamp;
  std::string action;
  std::string change_id;
  std::string summary;
  std::string outcome;
};

class AuditInspector {
 public:
  explicit AuditInspector(std::filesystem::path audit_log_path =
                              "logs/autonomy_audit.log");

  std::vector<AuditEntry> RecentEntries(std::size_t limit) const;

 private:
  std::filesystem::path audit_log_path_;
};

}  // namespace game::ai
