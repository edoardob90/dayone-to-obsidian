# pylint: disable=too-many-arguments,line-too-long,no-value-for-parameter
"""import.py"""
from pathlib import Path

import click

from utils import process_journal
from rich_utils import verbose_msg, info_msg, progress


@click.command()
@click.argument(
    "folder",
    type=click.Path(exists=True, file_okay=False),
)
@click.option(
    "--vault-directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Obsidian vault directory where you will copy the exported Markdown files. "
    "If passed, the script will skip exporting already existent files. "
    "PLEASE NOTE: the script IS NOT perfoming any copy operation, which must be done manually",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Overwrite output files, even if they are present in the vault directory. "
    "Makes sense only with --vault-directory",
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
    "--tag-prefix",
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
    "-sep",
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
@click.option(
    "--status-tags",
    "-s",
    multiple=True,
    default=[None],
    help="Add this tag as '#status/' tag, e.g., '-s Draft' becomes '#status/draft'. Can be used multiple times",
)
def convert(
    verbose: int,
    tag_prefix: str,
    folder: click.Path,
    vault_directory: click.Path,
    force: bool,
    convert_links: bool,
    yaml: bool,
    merge_entries: bool,
    entries_separator: str,
    ignore_tags: tuple,
    ignore_from: click.File,
    status_tags: tuple,
):
    """Converts DayOne entries into markdown files suitable to use as an Obsidian vault.
    Each journal will end up in a sub-folder named after the file (e.g.: Admin.json -> admin/). All JSON files
    in the FOLDER will be processed, remove those you don't want processed. The FOLDER will also be the destination
    for converted markdown files. After conversion you can open this folder as a vault in Obsidian. This is done
    to prevent accidental modification of an existing vault.

    FOLDER is where your DayOne exports reside and where the converted markdown files will be written.
    """
    if verbose != 0:
        verbose_msg(f"Verbose mode enabled. Verbosity level: [blue]{verbose}[/blue]")

        if yaml:
            info_msg("Each entry will have a YAML frontmatter")
        else:
            info_msg("No YAML frontmatter will be added")

        if convert_links:
            info_msg(
                ":arrows_clockwise: Converting Day One internal links to Obsidian (when possible)"
            )

    # Build the list of tags to ignore
    if ignore_from is not None:
        _ignore_tags = ignore_from.readlines()
        ignore_tags += tuple(x.strip("\n") for x in _ignore_tags)

    # Convert a tuple to a set to discard duplicate tags, if any
    ignore_tags = set(filter(bool, ignore_tags))

    if verbose > 1:
        verbose_msg(f"Ignoring the following tags: {', '.join(ignore_tags)}")

    # Status tags, if any
    status_tags = set(filter(bool, status_tags))

    if verbose > 0:
        info_msg(f"Assigned status tags: {status_tags}")

    # Process each JSON journal file in the input folder
    info_msg("[bold green]Processing journals...")
    with progress:
        for filename in Path(folder).glob("[!0-9]*.json"):
            process_journal(
                progress=progress,
                journal=filename,
                vault_directory=vault_directory,
                force=force,
                tag_prefix=tag_prefix,
                verbose=verbose,
                convert_links=convert_links,
                yaml=yaml,
                merge_entries=merge_entries,
                entries_separator=entries_separator,
                ignore_tags=ignore_tags,
                status_tags=status_tags,
            )
    info_msg(
        "[bold green] :white_check_mark: All JSON journals (if any) have been processed!"
    )


if __name__ == "__main__":
    convert()
