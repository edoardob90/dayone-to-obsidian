# dayone-to-obsidian

Convert a [Day One](https://dayoneapp.com/) JSON export into individual entries for [Obsidian](https://obsidian.md).

Heavily based off of the work from [QuantumGardener](https://github.com/quantumgardener/dayone-to-obsidian) with a few improvements.

## Added features of this repo

Check the `--help` option to get a description of the new features. In summary:

- Process audio, video, and pdf attachments as well
- Toggle on/off YAML frontmatter (if you don't want it or use it)
- Add option `--convert-links` to replace internal DayOne links (e.g., `dayone://view?entryId=<UUID>`) with Obsidian links
- Status tags can be added with the `--status-tags` (or `-s`). Each `tag` passed as argument will be added as `#status/tag`
- Add the option `--merge-entries` to merge entries (with a custom separator) with the same date instead of creating multiple files

## Installation

- Clone the repository
- Run `poetry install`
- Run `poetry run python convert.py path/to/dayone/export/folder`

You can also run **without Poetry**: you can simply create a virtual environment and run `pip install -r requirements.txt` since the script requires only a couple of packages not in Python standard library.

## Day One version

This script works with journals exported as JSON from DayOne, version **7.16** (build 1421) as of September, 21st 2022.

## Usage

| :warning: WARNING                                    |
| :--------------------------------------------------- |
| This script deletes folders if run a second time     |
| You are responsible for ensuring against data loss   |
| This script renames files (media files, JSON export) |

1. Export your journal from [Day One in JSON format](https://help.dayoneapp.com/en/articles/440668-exporting-entries)
2. Expand that zip file
3. Run the script as shown above
4. Check the results in Obsidian by opening the folder as a vault
5. Move the _journal name_ and attachments folders to another (or your) vault.

When done, the script renames the journal JSON file by prepending a number, starting with 0. Renamed JSON files will be **ignored** if the script is run another time.

_Suggestion:_ to move the resulting Markdown files, it's convenient to use `rsync`. For example,

```bash
rsync -R -av --inplace --update export_folder/ vault_folder/
```

and `rsync` will re-create the exact folder structure.

## Features

### Config file

**:warning: CHANGE:** Config file format is TOML, as it's natively supported (read-only) from **Python 3.11.x**.

If you want to import the same journal periodically, you ideally want to run the `convert.py` script with the same options. For this purpose, the script supports reading a TOML configuration file with the `-c/--config` option.

The config file recognizes keywords with the same names as command-line options. Additionally, you can add a `metadata` key which contains any extra metadata field you might want to add to **each entry**. Added metadata adhere to the [syntax of the Dataview plugin](https://blacksmithgu.github.io/obsidian-dataview/annotation/add-metadata/).

Command-line options have precedence on the corresponding key-value in the config file, i.e., you can use a command-line option to override whatever value is set in the config file.

The only keys which are **not** discarded when the equivalent command-line option is passed are `ignore_tags` and `status_tags`. In this case, the values passed on the command-line are **merged** with those found in the config file (if any).

An example of a valid `config.toml` is:

```toml
vault_directory = "~/path/to/my/journal/folder/"
yaml = true
yaml_fields = ["Field 1", "Field 2"]
merge_entries = true
convert_links = false
ignore_tags = [ "First tag to ignore", "Another tag to ignore" ]
status_tags = [ "Draft", "From email" ]

[metadata]
ignore = [ "Ignore this field", "And this" ]
tags = [ "Additional tag 1", "Additional tag 2" ]

# Extra metadata fields can be added as well
[metadata.extra]
up = "A new metadata field named \"up\" will be added"
note = '''
This note field can be a
multiline text.
It can also contain

empty lines, if that's what you want.
'''
```

### Metadata formatting

The metadata formatting choices were dictated by purely personal criteria. In other words, the files are formatted the way I want them in my Obsidian vault.

The config file allows you to tweak two aspects of each entry's metadata:

1. The `yaml_fields` (a list) key controls which fields are added to the YAML frontmatter (if enabled) and which ones are visible at the top of the entry.
2. The `ignore` key (a list) in the `metadata` section which fields are completely discarded.

Currently, the available fields (names are **case insensitive**) read from Day One JSON are the following:

- `created`: creation date & time (ISO 8601 format)
- `place`: street, city, country
- `lat`, `lon`: GPS coordinates
- `weather`: weather conditions
- `journal`: the journal name
- `favorite`: whether the entry is starred
- `url`: an external link to open the entry in Day One

By default, `yaml_fields` is an **empty list**, which means that all the above metadata fields will be added at the top of each entry.

For example: you want that each entry in Obsidian has only the tags as a visibile metadata fields, while you want to ignore the journal name and discard whether an entry is starred. You can achieve that with the following config file:

```toml
yaml = true
yaml_fields = ["created", "place", "lat", "lon", "weather"]

[metadata]
ignore = ["journal", "favorite"]
tags = ["Additional tag 1"]

[metadata.extra]
my_custom_field = "My custom value"
```

## Todo

Features that I'm considering:

- [x] ~~Specify the vault destination folder to skip files that are already present~~
- [x] ~~Add possibility to read in options from a config file (ideally a `config.yaml`)~~
- [ ] Support choosing which metadata fields are included in the YAML frontmatter (right now, only `location`, `places`, `dates`, and `tags` are added if `has_yaml` is set to `true` in the config file or the option `--yaml` is passed)
- [ ] Add the possibility to customize metadata formatting (not sure to which template it should adhere)
- [ ] Implement a copy with `rsync`
- [ ] Auto-unzip of the exported journal
