# paper-trail-marketplace

A Claude Code plugin marketplace. Currently ships one plugin:

- **paper-trail** — turns Claude's reading/writing into pages of paper, per
  session and per model. See `paper-trail/README.md` for full details.

## Install

Add the marketplace from GitHub, then install the plugin:

```
/plugin marketplace add Ink01101011/paper-trail-marketplace
/plugin install paper-trail@paper-trail
```

(The marketplace is named `paper-trail`, hence the `@paper-trail` suffix — the
`paper-trail-marketplace` in the `add` command is just the GitHub repo name.)

Working from a local checkout instead? Point `marketplace add` at the
**directory** that contains `.claude-plugin/marketplace.json` (not the file
itself):

```
/plugin marketplace add /absolute/path/to/paper-trail-marketplace
/plugin install paper-trail@paper-trail
```

Refresh after changes:

```
/plugin marketplace update paper-trail
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
