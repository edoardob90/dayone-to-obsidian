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
- Run `poetry run python import.py path/to/folder`

You can also run **without Poetry**: you can simply create a virtual environment and run `pip install -r requirements.txt` since the script requires only a couple of packages not in Python standard library.

## Day One version

This script works with journals exported from DayOne, version **7.16** (build 1421) as of September, 21st 2022.

## Setup

| :warning: WARNING                                  |
| :------------------------------------------------- |
| This script deletes folders if run a second time   |
| You are responsible for ensuring against data loss |
| This script renames files (namely, media files)    |

1. Export your journal from [Day One in JSON format](https://help.dayoneapp.com/en/articles/440668-exporting-entries)
2. Expand that zip file
3. Run the script as shown above
4. Check results in Obsidian by opening the folder as a vault
5. If happy, move each _journal name_, _photos_, and _pdfs_ folders to another vault.

_Suggestion:_ to move the outputted Markdown files, it's convenient to use `rsync`. For example,

```bash
rsync -R -av --inplace --update export_folder/ vault_folder/
```

and `rsync` will re-create the exact folder structure.

## Features

### Metadata formatting

The metadata formatting choices were dictated by purely personal criteria. In other words, the files are formatted the way I want them in my Obsidian vault.

An example of a metadata block:

```
up:: [[Obsidian link]]
dates:: <entry date (YYYY-MM-DD)>
time:: <entry time (HH:MM, localized)>
places:: <entry address>
location:: <GPS coordinates (if present)>
weather:: <weather conditions>
tags:: #prefix/tag1, #prefix/tag2 #status/statusTag1 #place/country/region/town
%%uuid:: <entry UUID>%%
```

That said, the formatting can be adapted to one's purposes very easily. Take a look at the definition of the `Entry` class at the beginning of `utils.py` and adjust the `__str__` method to change the formatting.

## Todo

Features I'm considering:

- [x] Specify the vault destination folder to skip files that are already present
- [ ] Implement a copy with `rsync`
- [ ] Auto-unzip of the exported journal
- [ ] Add possibility to read in options from a config file (ideally a `config.yaml`)
