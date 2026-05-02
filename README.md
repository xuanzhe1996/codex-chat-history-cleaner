# Codex Chat History Cleaner

这是一个用于清理本地 Codex 聊天历史残留的 Codex skill。它适用于排查和清理归档会话、搜索索引残留、聊天 transcript 文件，以及“清理过程本身又被当前会话记录下来”导致的自引用搜索命中。

## 包含内容

- `SKILL.md`：可复用的 Codex skill 流程和安全边界。
- `scripts/clean_codex_history.py`：确定性的清理脚本。默认只做 dry-run 检查，只有传入 `--execute` 才会修改文件。
- `references/privacy.md`：发布或分享清理流程前的隐私检查清单。
- `agents/openai.yaml`：Codex skill 展示和触发所需的元数据。
- `.gitignore`：防止误提交本地 Codex 状态、聊天记录、认证文件、数据库、截图和备份文件。

## 使用示例

先只检查，不做修改：

```bash
python3 scripts/clean_codex_history.py --codex-home "$HOME/.codex" --dry-run
```

确认 dry-run 结果后，删除本地已归档的 Codex 会话：

```bash
python3 scripts/clean_codex_history.py --codex-home "$HOME/.codex" --all-archived --execute
```

## 安全提醒

这个工具操作的是本地 Codex 状态文件。建议总是先运行 `--dry-run`，确认将要处理的范围后再执行。默认会在修改数据库或索引前创建备份，除非你明确传入 `--no-backup`。

如果目标是清掉搜索残留，尽量不要在新的清理对话里打印私密聊天标题、完整 thread ID 或本机绝对路径，否则当前清理对话可能会变成新的搜索命中。
