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

If you want to import the same journal periodically, you ideally want to run the `convert.py` script with the same options. For this purpose, the script supports reading a YAML configuration file with the `-c/--config` option.

The YAML config file recognizes keywords with the same names as command-line options. Additionally, you can add a `metadata` key which contains any extra metadata field you might want to add to **each entry**. Added metadata adhere to the [syntax of the Dataview plugin](https://blacksmithgu.github.io/obsidian-dataview/annotation/add-metadata/).

Command-line options have precedence on the corresponding key-value in the config file, i.e., you can use a command-line option to override whatever value is set in the config file.

The only keys which are **not** discarded when the equivalent command-line option is passed are `ignore_tags` and `status_tags`. In this case, the values passed on the command-line are **merged** with those found in the config file (if any).

An example of a valid `config.yaml` is:

```yaml
vault_directory: ~/path/to/my/journal/folder/
yaml: true
merge_entries: true
convert_links: false
ignore_tags:
  - First tag to ignore
  - Another tag to ignore
status_tags:
  - Draft
  - From email
metadata:
  up: 'A new metadata field named "up" will be added'
  note: |
    This note field can be a
    multiline text.
    It can also contain

    empty lines, if that's what you want.

  # Additional tags will be added to EVERY entry
  # Make sure this is what you want
  tags:
    - Additional tag 1
    - Additional tag 2
```

A few notes about the YAML format:

- YAML doesn't require strings to be quoted. However, you might want to quote them to preserve their content as-is.
- If a key has no value, Python assigns a default `None` value to that key.

### Metadata formatting

The metadata formatting choices were dictated by purely personal criteria. In other words, the files are formatted the way I want them in my Obsidian vault.

An example of a metadata block:

```
dates:: <entry date (YYYY-MM-DD)>
time:: <entry time (HH:MM, localized)>
places:: <entry address>
location:: <GPS coordinates (if present)>
weather:: <weather conditions>
tags:: #journal/journalName #prefix/tag1, #prefix/tag2 #status/statusTag1
url:: [DayOne](dayone://view?entryId=<uuid>)
```

That said, the formatting can be adapted to one's purposes very easily. If you are comfortable in editing the source code and have some experience with Python, take a look at the definition of the `Entry` class in the `entry.py` source file and adjust [the `__str__` method](https://github.com/edoardob90/dayone-to-obsidian/blob/ba3c1079a84dc7abe005d479c06eaa727c22bb29/entry.py#L28-L44) to change the string representation (i.e., how it will be written to file) of an entry.

## Todo

Features that I'm considering:

- [x] ~~Specify the vault destination folder to skip files that are already present~~
- [x] ~~Add possibility to read in options from a config file (ideally a `config.yaml`)~~
- [ ] Support choosing which metadata fields are included in the YAML frontmatter (right now, only `location`, `places`, `dates`, and `tags` are added if `has_yaml` is set to `true` in the config file or the option `--yaml` is passed)
- [ ] Add the possibility to customize metadata formatting (not sure to which template it should adhere)
- [ ] Implement a copy with `rsync`
- [ ] Auto-unzip of the exported journal
