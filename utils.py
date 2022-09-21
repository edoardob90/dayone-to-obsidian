# pylint: disable=too-many-nested-blocks,too-many-branches,too-many-locals,line-too-long,invalid-name
"""utils.py"""
import json
import re
import shutil
from typing import Dict, OrderedDict, Set
from datetime import datetime
from pathlib import Path

import click
import dateutil.parser
import pytz
from rich.progress import track


def capwords(string: str, sep: str = "") -> str:
    """Capitalize the first letter of each word in a string"""
    return sep.join(word[0].upper() + word[1:].lower() for word in string.split(" "))


def retrieve_metadata(
    entry: Dict,
    local_date: datetime,
    tag_prefix: str,
    ignore_tags: set,
    verbose: int = 0,
) -> Dict:
    """Fetch the metadata of a single journal entry"""
    metadata = {}
    metadata["uuid"] = entry["uuid"]

    # Add raw create datetime adjusted for timezone and identify timezone
    metadata["dates"] = local_date.isoformat()
    metadata["timezone"] = entry["timeZone"]

    # Add location
    location = []
    try:
        location = list(
            filter(
                None,
                [
                    entry["location"].get(key, None)
                    for key in (
                        "placeName",
                        "localityName",
                        "administrativeArea",
                        "country",
                    )
                ],
            )
        )
    except KeyError:
        if verbose and verbose > 1:
            click.echo(
                f"Entry with date '{local_date.strftime('%Y-%m-%d')}' has no location!"
            )

    metadata["places"] = ", ".join(location)

    # Add GPS, not all entries have this
    if "location" in entry and all(
        ["latitude" in entry["location"], "longitude" in entry["location"]]
    ):
        lat = entry["location"]["latitude"]
        lon = entry["location"]["longitude"]

        metadata["location"] = f"{lat}, {lon}"

    # Add weather information if present
    if "weather" in entry and all(
        i in entry["weather"]
        for i in ["conditionsDescription", "temperatureCelsius", "windSpeedKPH"]
    ):
        weather = entry["weather"]
        metadata[
            "weather"
        ] = f"{weather['conditionsDescription']}, {round(weather['temperatureCelsius'], 1)}°C, {round(weather['windSpeedKPH'], 1)} km/h wind"

    # TODO: do I want to keep track of user activity? (most likely no)
    # Add user activity if present
    # if "userActivity" in entry:
    #     activity = entry["userActivity"]
    #     if "activityName" in activity:
    #         metadata.append(
    #             MetadataEntry(name="Activity", description=activity["activityName"])
    #         )

    #     if "stepCount" in activity and activity["stepCount"] > 0:
    #         metadata.append(
    #             MetadataEntry(name="Steps", description=activity["stepCount"])
    #         )

    # Process tags
    tags = []
    if "tags" in entry:
        for tag in entry["tags"]:
            if tag not in ignore_tags:
                # format the tag: remove spaces and capitalize each word
                # Example: #Original tag --> #{prefix}/originalTag
                new_tag = capwords(f"{tag_prefix}{tag}")
                tags.append(new_tag)

    # Add a tag for the location to make places searchable in Obsidian
    if location:
        tags.append(f"#places/{'/'.join(map(capwords, location[-1:0:-1]))}")

    # Add a :heart: emoji for starred entries
    if entry["starred"]:
        tags.append("#\u2764")

    # Build the final string with all the tags
    if tags:
        metadata["tags"] = ", ".join(tags)

    return metadata


def process_journal(
    journal: Path,
    tag_prefix: str,
    verbose: int,
    convert_links: bool,
    yaml: bool,
    merge_entries: bool,
    entries_separator: str,
    ignore_tags: Set,
) -> None:
    """Process a journal JSON file"""

    if verbose != 0:
        click.echo(f"Verbose mode enabled. Verbosity level: {verbose}")

    journal_name = (
        journal.stem.lower()
    )  # name of folder where journal entries will end up in your Obsidian vault
    base_folder = journal.resolve().parent
    journal_folder = base_folder / journal_name

    # Clean out existing journal folder, otherwise each run creates new files
    if journal_folder.exists():
        if verbose > 0:
            click.echo(f"Deleting existing folder: {journal_folder}")
        shutil.rmtree(journal_folder)

    if verbose > 0:
        click.echo(f"Creating {journal_folder}")
    journal_folder.mkdir()

    if yaml and verbose > 0:
        click.echo("Each entry will have a YAML frontmatter")
        if verbose > 1:
            click.echo(
                "YAML frontmatter will contain 'Location', 'Location Name', and 'Tags'"
            )
    elif verbose > 0:
        click.echo("No YAML frontmatter will be added")

    click.echo(f"Begin processing entries for '{journal.name}'")

    # All entries processed will be added to a ordered dictionary
    entries = OrderedDict()

    # Mapping between entries UUIDs and Markdown files
    # Needed to perform DayOne -> Obsidian links conversion
    uuid_to_file = {}

    with open(journal, encoding="utf-8") as json_file:
        data = json.load(json_file)
        for entry in track(data["entries"]):
            new_entry = []

            creation_date = dateutil.parser.isoparse(entry["creationDate"])
            local_date = creation_date.astimezone(
                pytz.timezone(entry["timeZone"])
            )  # It's natural to use our local date/time as reference point, not UTC

            # Fetch entry's metadata
            metadata = retrieve_metadata(
                entry, local_date, tag_prefix, ignore_tags=ignore_tags, verbose=verbose
            )

            # Add some metadata as a YAML front matter
            if yaml:
                new_entry.append("---\n")
                for name, description in metadata.items():
                    if name in ["location", "places", "tags"]:
                        new_entry.append(
                            f"{name.lower().replace(' ', '_')}: {description}\n"
                        )
                new_entry.append("---\n\n")

            # Start Metadata section
            # newEntry.append( '%%\n' ) # uncomment to hide metadata
            new_entry.append("up:: [[Day One MOC]]\n")
            entry_uuid = metadata.pop("uuid", None)
            for name, description in metadata.items():
                new_entry.append(f"{name}:: {description}\n")
            new_entry.append("\n\n")

            # Add body text if it exists (can have the odd blank entry), after some tidying up
            try:
                new_text = entry["text"].replace("\\", "")
                new_text = new_text.replace("\u2028", "\n")
                new_text = new_text.replace("\u1C6A", "\n\n")
                new_text = new_text.replace("\u200b", "")

                # Fixes multi-line ```code blocks```
                # DayOne breaks these block in many lines with a triple ``` delimiters.
                # This results in a bad formatting of the Markdown output.
                new_text = re.sub(r"```\s+```", "", new_text, flags=re.MULTILINE)

                # Handling attachments: photos, audios, videos, and documents (PDF)

                if "photos" in entry:
                    # Correct photo links. The filename is the md5 code, not the identifier used in the text
                    for photo in entry["photos"]:
                        image_type = photo["type"]
                        original_photo_file = (
                            base_folder / "photos" / f"{photo['md5']}.{image_type}"
                        )
                        renamed_photo_file = (
                            base_folder
                            / "photos"
                            / f"{photo['identifier']}.{image_type}"
                        )
                        if original_photo_file.exists():
                            if verbose > 1:
                                click.echo(
                                    f"Renaming {original_photo_file} to {renamed_photo_file}"
                                )
                            original_photo_file.rename(renamed_photo_file)

                        new_text = re.sub(
                            r"(\!\[\]\(dayone-moment:\/\/)([A-F0-9]+)(\))",
                            (r"![[\2.{}]]".format(image_type)),
                            new_text,
                        )

                if "pdfAttachments" in entry:
                    # Correct photo pdf links. Similar to what is done on photos
                    for pdf in entry["pdfAttachments"]:
                        original_pdf_file = base_folder / "pdfs" / f"{pdf['md5']}.pdf"
                        renamed_pdf_file = (
                            base_folder / "pdfs" / f"{pdf['identifier']}.pdf"
                        )
                        if original_pdf_file.exists():
                            if verbose > 1:
                                click.echo(
                                    f"Renaming {original_pdf_file} to {renamed_pdf_file}"
                                )
                            original_pdf_file.rename(renamed_pdf_file)

                        new_text = re.sub(
                            r"(\!\[\]\(dayone-moment:\/pdfAttachment\/)([A-F0-9]+)(\))",
                            r"![[\2.pdf]]",
                            new_text,
                        )

                if "audios" in entry:
                    for audio in entry["audios"]:
                        # Audio type is missing in DayOne JSON
                        # AAC files are very often saved with .m4a extension
                        audio_format = "m4a"
                        original_audio_file = (
                            base_folder / "audios" / f"{audio['md5']}.{audio_format}"
                        )
                        renamed_audio_file = (
                            base_folder
                            / "audios"
                            / f"{audio['identifier']}.{audio_format}"
                        )
                        if original_audio_file.exists():
                            if verbose > 1:
                                click.echo(
                                    f"Renaming {original_audio_file} to {renamed_audio_file}"
                                )
                            original_audio_file.rename(renamed_audio_file)

                        new_text = re.sub(
                            r"(\!\[\]\(dayone-moment:\/audio/)([A-F0-9]+)(\))",
                            r"![[\2.{}]]".format(audio_format),
                            new_text,
                        )

                if "videos" in entry:
                    for video in entry["videos"]:
                        video_format = video["type"]
                        original_video_file = (
                            base_folder / "videos" / f"{video['md5']}.{video_format}"
                        )
                        renamed_video_file = (
                            base_folder
                            / "videos"
                            / f"{video['identifier']}.{video_format}"
                        )
                        if original_video_file.exists():
                            if verbose > 1:
                                click.echo(
                                    f"Renaming {original_video_file} to {renamed_video_file}"
                                )
                            original_video_file.rename(renamed_video_file)

                        new_text = re.sub(
                            r"(\!\[\]\(dayone-moment:\/video/)([A-F0-9]+)(\))",
                            r"![[\2.{}]]".format(video_format),
                            new_text,
                        )

                new_entry.append(new_text)

                # Add the entry's uuid as an hidden
                new_entry.append(f"\n\n%%\nuuid:: {entry_uuid}\n")

            except KeyError:
                pass

            # Save entries organised by year, year-month, year-month-day.md
            year_dir = journal_folder / str(creation_date.year)
            month_dir = year_dir / creation_date.strftime("%Y-%m")

            if not year_dir.exists():
                year_dir.mkdir()

            if not month_dir.is_dir():
                month_dir.mkdir()

            # Target filename to save to. Will be modified if already exists
            file_date_format = local_date.strftime("%Y-%m-%d")
            target_file = month_dir / f"{file_date_format}.md"

            # Here is where we handle multiple entries on the same day. Each goes to it's own file
            if target_file.stem in entries:
                if verbose > 1:
                    click.echo(
                        f"Found another entry with the same date '{target_file.stem}'"
                    )
                if not merge_entries:
                    # File exists, need to find the next in sequence and append alpha character marker
                    index = 97  # ASCII a
                    target_file = month_dir / f"{file_date_format}{chr(index)}.md"
                    while target_file.stem in entries:
                        index += 1
                        target_file = month_dir / f"{file_date_format}{chr(index)}.md"
                else:
                    prev_entry, _ = entries.pop(target_file.stem)
                    new_entry = (
                        prev_entry + [f"\n\n{entries_separator}\n\n"] + new_entry
                    )

            # Add current entry's as a new key-value pair in entries dict
            entries[target_file.stem] = new_entry, target_file

            # Step 1 to replace dayone internal links to other entries with proper Obsidian [[links]]
            uuid_to_file[entry_uuid] = target_file.name

        click.echo(f"Complete: {len(data['entries'])} entries processed.")

    if convert_links:
        click.echo("Converting Day One internal links to Obsidian (when possible)")

        # Step 2 to replace dayone internal links: we must do a second iteration over entries
        # A replacement function for dayone internal links
        def replace_link(match: re.Match) -> str:
            link_text, uuid = match.groups()
            if uuid in uuid_to_file:
                return f"[[{uuid_to_file[uuid]}|{link_text}]]"
            return f"^[Linked entry with UUID `{uuid}` not found]"

        # The regex to match a dayone internal link: [link_text](dayone://view?EntryId=uuid)
        regex = re.compile(r"\[(.*?)\]\(dayone2?:\/\/.*?([A-F0-9]+)\)")

    for entry in entries.values():
        text, target_file = entry
        # an entry is a list of string, so we need to concat all of them
        text = "".join(text)

        if convert_links:
            text = re.sub(regex, replace_link, text)

        with open(target_file, "w", encoding="utf-8") as fp:
            fp.write(text)

    click.echo(f"Done. Entries have been exported to '{journal_folder}'.")
