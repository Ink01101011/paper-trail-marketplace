# paper-trail-marketplace

A Claude Code plugin marketplace. Currently ships one plugin:

- **paper-trail** — turns Claude's reading/writing into pages of paper, per
  session and per model. See `paper-trail/README.md` for full details.

## Install

This is a local marketplace (the plugin folder sits next to
`.claude-plugin/marketplace.json`).

```
/plugin marketplace add /absolute/path/to/paper-trail-marketplace
/plugin install paper-trail@paper-trail-marketplace
```

Point `marketplace add` at the **directory** that contains
`.claude-plugin/marketplace.json`, not the file itself.

To publish it instead, push this folder to a git repo and add it by URL:

```
/plugin marketplace add your-org/paper-trail-marketplace
```

Refresh after changes:

```
/plugin marketplace update paper-trail-marketplace
```

## Layout

```
paper-trail-marketplace/
├── .claude-plugin/
│   └── marketplace.json     # lists the plugins
└── paper-trail/             # the plugin itself
    ├── .claude-plugin/plugin.json
    ├── hooks/hooks.json
    ├── scripts/
    └── skills/pages/
```
