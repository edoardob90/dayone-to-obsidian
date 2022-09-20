# pylint: disable=too-many-arguments
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
def convert(
    verbose,
    tags_prefix,
    folder,
    convert_links,
    yaml,
    merge_entries,
    entries_separator,
):
    """Converts DayOne entries into markdown files suitable to use as an Obsidian vault.
    Each journal will end up in a sub-folder named after the file (e.g.: Admin.json -> admin/). All JSON files
    in the FOLDER will be processed, remove those you don't want processed. The FOLDER will also be the destination
    for converted markdown files. After conversion you can open this folder as a vault in Obsidian. This is done
    to prevent accidental modification of an existing vault.

    FOLDER is where your DayOne exports reside and where the converted markdown files will be written.
    """
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
        )


if __name__ == "__main__":
    convert()
