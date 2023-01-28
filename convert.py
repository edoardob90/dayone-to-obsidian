# pylint: disable=too-many-arguments,line-too-long,no-value-for-parameter
"""convert.py"""
import pathlib

import click
import tomllib

from rich_utils import info_msg, progress, verbose_msg, warn_msg
from utils import process_journal


@click.command()
@click.argument(
    "folder",
    type=click.Path(exists=True, file_okay=False),
)
@click.option(
    "--config",
    "-c",
    "config_file",
    type=click.Path(dir_okay=False, file_okay=True, path_type=pathlib.Path),
    help="A TOML configuration file. Check the README for its syntax/options",
)
@click.option(
    "--vault-directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Obsidian vault directory where you will copy the exported Markdown files. "
    "If passed, the script will skip exporting already existent files. "
    "PLEASE NOTE: the script IS NOT performing any copy operation, which must be done manually",
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
    help="Replace DayOne internal links with Obsidian [[links]]. Default is 'False'",
    default=False,
    is_flag=True,
)
@click.option(
    "--tag-prefix",
    help="Prefix to add as part of the tag name for sub-tags. Default is '#on/'",
    default=None,
)
@click.option(
    "--status-prefix",
    help="Prefix for status tags. Default is '#status/'",
    default=None,
)
@click.option(
    "--merge-entries",
    help="Combine entries with the same date in a single file. Default is 'False'",
    is_flag=True,
    default=False,
)
@click.option(
    "--entries-sep",
    help="String to use to separate merged entries. Default is a double '---'",
    default=None,
)
@click.option(
    "--ignore-tags",
    "-i",
    multiple=True,
    help="Ignore this tag. Can be used multiple times, e.g., -i 'Tag1' -i 'Tag2'",
    default=[None],
)
@click.option(
    "--status-tags",
    "-s",
    multiple=True,
    default=[None],
    help="Add this tag as '#status/' tag, e.g., '-s Draft' becomes '#status/draft'. Can be used multiple times",
)
def convert(
    folder: click.Path,
    config_file: click.Path,
    verbose: int,
    tag_prefix: str,
    status_prefix: str,
    vault_directory: click.Path,
    force: bool,
    convert_links: bool,
    yaml: bool,
    merge_entries: bool,
    entries_sep: str,
    ignore_tags: tuple,
    status_tags: tuple,
):
    """Converts DayOne entries into markdown files suitable to use as an Obsidian vault.
    Each journal will end up in a sub-folder named after the file (e.g., Personal.json -> Personal/). All JSON files
    in the FOLDER will be processed, **except** those whose filename starts with a number. Prepend any number to those files you want to exclude.
    The FOLDER will also be the destination for converted markdown files. After conversion you can open this folder as a vault in Obsidian.

    FOLDER is where your DayOne JSON exports reside and where the converted markdown files will be written.
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

    # Read the config file
    config = {}
    if config_file is not None and config_file.exists():
        with config_file.open(mode="rb") as file:
            config: dict = tomllib.load(file)

    # Build the list of tags to ignore
    if (tags_to_ignore := config.get("ignore_tags")) is not None and tags_to_ignore:
        ignore_tags += tuple(tags_to_ignore)
    # Convert a tuple to a set to discard duplicate tags, if any
    # `filter` discards the `None` tag that's added by default to `ignore_tags` when the option is not passed
    ignore_tags = set(filter(bool, ignore_tags))

    if verbose > 1 and ignore_tags:
        verbose_msg(f"Ignoring tags: {', '.join(ignore_tags)}")

    # Status tags, if any
    if (tags_as_status := config.get("status_tags")) is not None and tags_as_status:
        status_tags += tuple(tags_as_status)
    status_tags = set(filter(bool, status_tags))

    if verbose > 1 and status_tags:
        info_msg(f"Status tags: {', '.join(status_tags)}")

    # Process each JSON journal file in the input folder
    info_msg("[bold green]Processing journals...")
    if verbose > 0:
        warn_msg("Journal filenames with a leading number will be ignored!")

    with progress:
        for filename in pathlib.Path(folder).glob("[!0-9]*.json"):
            process_journal(
                progress=progress,
                journal=filename,
                vault_directory=vault_directory or config.get("vault_directory", None),
                force=force,
                verbose=verbose,
                ignore_tags=ignore_tags,
                status_tags=status_tags,
                tag_prefix=tag_prefix or config.get("tag_prefix", "#on"),
                status_prefix=status_prefix or config.get("status_prefix", "#status"),
                convert_links=convert_links or config.get("convert_links", False),
                yaml=yaml or config.get("yaml", False),
                yaml_fields=config.get("yaml_fields", None),
                merge_entries=merge_entries or config.get("merge_entries", False),
                entries_sep=entries_sep or config.get("entries_sep", "---\n---"),
                metadata_ext=config.get("metadata", None),
            )

    info_msg(
        "[bold green]:white_check_mark: All JSON journals (if any) have been processed!"
    )


if __name__ == "__main__":
    convert()
