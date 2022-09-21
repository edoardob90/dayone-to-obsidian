# pylint: disable=too-many-arguments,line-too-long,no-value-for-parameter
"""import.py"""
from pathlib import Path

import click

from utils import process_journal


@click.command()
@click.argument(
    "folder",
    type=click.Path(exists=True, file_okay=False),
)
@click.option("-v", "--verbose", count=True, help="Turn on verbose logging")
@click.option("--yaml/--no-yaml", help="Add a YAML frontmatter", default=False)
@click.option(
    "--convert-links",
    help="Replace DayOne internal links with Obsidian [[links]]",
    default=False,
    is_flag=True,
)
@click.option(
    "--tags-prefix",
    help="Prefix to add as part of the tag name for sub-tags. Default is '#on'",
    default="#on/",
)
@click.option(
    "--merge-entries",
    help="Combine entries with the same date in a single file",
    is_flag=True,
    default=False,
)
@click.option(
    "--entries-separator",
    "-s",
    help="String to use to separate merged entries. Default is a double '---'",
    default="---\n---",
)
@click.option(
    "--ignore-tags",
    "-i",
    multiple=True,
    help="Ignore this tag. Can be used multiple times, e.g., -i 'Tag1' -i 'Tag2'",
    default=[None],
)
@click.option(
    "--ignore-from",
    type=click.File(encoding="utf-8"),
    help="File containing tags to ignore, one per line. Can be used in combination with '-i': in such case, ignored tags are combined",
    default=None,
)
def convert(
    verbose: int,
    tags_prefix: str,
    folder: click.Path,
    convert_links: bool,
    yaml: bool,
    merge_entries: bool,
    entries_separator: str,
    ignore_tags: tuple,
    ignore_from: click.File,
):
    """Converts DayOne entries into markdown files suitable to use as an Obsidian vault.
    Each journal will end up in a sub-folder named after the file (e.g.: Admin.json -> admin/). All JSON files
    in the FOLDER will be processed, remove those you don't want processed. The FOLDER will also be the destination
    for converted markdown files. After conversion you can open this folder as a vault in Obsidian. This is done
    to prevent accidental modification of an existing vault.

    FOLDER is where your DayOne exports reside and where the converted markdown files will be written.
    """
    # Build the list of tags to ignore
    if ignore_from is not None:
        _ignore_tags = ignore_from.readlines()
        ignore_tags += tuple(x.strip("\n") for x in _ignore_tags)

    # Convert a tuple to a set to discard duplicate tags, if any
    ignore_tags = set(ignore_tags)

    # Process each JSON journal file in the input folder
    for filename in Path(folder).glob("*.json"):
        process_journal(
            filename,
            tags_prefix,
            verbose,
            convert_links,
            yaml,
            merge_entries,
            entries_separator,
            ignore_tags,
        )


if __name__ == "__main__":
    convert()
