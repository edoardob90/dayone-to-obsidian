# pylint: disable=too-many-nested-blocks,too-many-branches,too-many-locals,line-too-long,invalid-name,consider-using-f-string
"""utils.py"""
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Set

import dateutil.parser
import pytz
from rich.progress import Progress

from rich_utils import info_msg, verbose_msg, warn_msg


@dataclass
class Entry:
    """A single journal entry"""

    uuid: str = None
    has_yaml: bool = False
    yaml: str = ""
    metadata: dict = field(default_factory=dict)
    text: str = ""
    output_file: Path = None

    def __str__(self) -> str:
        if self.has_yaml:
            self.yaml = "---\n{yaml_block}\n---\n\n".format(
                yaml_block="\n".join(
                    [
                        f"{name.lower().replace(' ', '_')}: {value}"
                        for name, value in self.metadata.items()
                        if name in ("location", "places", "dates", "tags")
                    ]
                )
            )
        metadata = [f"{name}:: {value}" for name, value in self.metadata.items()]
        return "{yaml}{metadata}\n%%uuid:: {uuid}%%\n\n{text}\n".format(
            yaml=self.yaml, metadata="\n".join(metadata), text=self.text, uuid=self.uuid
        )

    def add_metadata(self, *_, **kwargs):
        """Add metadata fields"""
        for name, value in kwargs.items():
            self.metadata[name] = str(value)

    def dump(self) -> None:
        """Write out entry to a file"""
        if self.output_file is None:
            raise RuntimeError("Entry output file is undefined!")
        with self.output_file.open("w", encoding="utf-8") as file:
            file.write(self.__str__())


def capwords(string: str, sep: str = "") -> str:
    """Capitalize the first letter of each word in a string"""
    return sep.join(word[0].upper() + word[1:].lower() for word in string.split(" "))


# TODO: refactor this function into a method of the Entry class
def retrieve_metadata(
    entry: Dict,
    local_date: datetime,
    tag_prefix: str,
    ignore_tags: Set,
    status_tags: Set,
    verbose: int = 0,
    journal_name: str = None,
) -> Dict:
    """Fetch the metadata of a single journal entry"""
    metadata = {}
    metadata["uuid"] = entry["uuid"]

    # Add raw create datetime adjusted for timezone and identify timezone
    metadata["dates"] = local_date.strftime("%Y-%m-%d")
    metadata["time"] = local_date.strftime("%H:%M:%S")
    # metadata["timezone"] = entry["timeZone"]

    # Add location
    location = []
    try:
        location = list(
            filter(
                bool,
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
            verbose_msg(
                f"Entry with date '{local_date.strftime('%Y-%m-%d')}' has no location!"
            )

    metadata["places"] = ", ".join(location)

    # Add GPS, not all entries have this
    if "location" in entry and all(
        ["latitude" in entry["location"], "longitude" in entry["location"]]
    ):
        loc = entry["location"]
        metadata["location"] = f"{loc.get('latitude')}, {loc.get('longitude')}"

    # Add weather information if present
    if "weather" in entry and all(
        i in entry["weather"]
        for i in ["conditionsDescription", "temperatureCelsius", "windSpeedKPH"]
    ):
        weather = entry["weather"]
        metadata[
            "weather"
        ] = f"{weather['conditionsDescription']}, {round(weather['temperatureCelsius'], 1)}°C, {round(weather['windSpeedKPH'], 1)} km/h wind"

    # Process tags
    tags = []

    # First tag is the journal name, if present
    if journal_name is not None:
        tags.append(capwords(f"#journal/{journal_name}"))

    if (entry_tags := entry.get("tags", None)) is not None:
        entry_tags = set(entry_tags)

        for tag in (entry_tags - ignore_tags) - status_tags:
            # format the tag: remove spaces and capitalize each word
            # Example: #Original tag --> #{prefix}/originalTag
            new_tag = capwords(f"{tag_prefix}{tag}")
            tags.append(new_tag)

        # Handle status tags
        if status_tags := entry_tags & status_tags:
            tags.extend(map(lambda tag: capwords("#status/" + tag), status_tags))

    # Add a tag for the location to make places searchable in Obsidian
    if location:
        tags.append(f"#places/{'/'.join(map(capwords, location[-1:0:-1]))}")

    # Add a :star: emoji for starred entries
    if entry["starred"]:
        tags.append("#\u2B50")

    # Build the final string with all the tags
    if tags:
        metadata["tags"] = ", ".join(tags)

    return metadata


def process_journal(
    progress: Progress,
    journal: Path,
    vault_directory: Path,
    tag_prefix: str,
    verbose: int,
    convert_links: bool,
    yaml: bool,
    force: bool,
    merge_entries: bool,
    entries_separator: str,
    ignore_tags: Set,
    status_tags: Set,
) -> None:
    """Process a journal JSON file"""
    # name of folder where journal entries will end up in your Obsidian vault
    journal_name = journal.stem.lower()
    base_folder = journal.resolve().parent
    journal_folder = base_folder / journal_name

    # Clean out existing journal folder, otherwise each run creates new files
    if journal_folder.exists():
        if verbose > 0:
            warn_msg(f"Deleting existing folder '{journal_folder}'")
        shutil.rmtree(journal_folder)

    if verbose > 0:
        info_msg(f"Creating '{journal_folder}'")
    journal_folder.mkdir()

    # All entries processed will be added to a dictionary
    entries = {}
    merged_entries = 0

    # Mapping between entries UUIDs and Markdown files
    # Needed to perform DayOne -> Obsidian links conversion
    uuid_to_file = {}

    with open(journal, encoding="utf-8") as json_file:
        data: Dict = json.load(json_file)

        task = progress.add_task(
            f"[bold green]Processing entries of '[cyan][not bold]{journal.name}[/not bold][/cyan]'",
            total=len(data["entries"]),
        )

        entry: Dict
        for entry in data["entries"]:
            new_entry = Entry()

            creation_date = dateutil.parser.isoparse(entry["creationDate"])
            local_date = creation_date.astimezone(
                pytz.timezone(entry["timeZone"])
            )  # It's natural to use our local date/time as reference point, not UTC

            # Fetch entry's metadata
            metadata = retrieve_metadata(
                entry,
                local_date,
                tag_prefix,
                ignore_tags=ignore_tags,
                status_tags=status_tags,
                journal_name=journal_name,
                verbose=verbose,
            )

            # Add some metadata as a YAML front matter
            if yaml:
                new_entry.has_yaml = True

            # Add entry's metadata
            new_entry.add_metadata(up="[[Day One MOC]]")
            new_entry.uuid = metadata.pop("uuid", None)
            new_entry.add_metadata(**metadata)

            # Add body text if it exists (entries can have a "blank body" sometimes), after some tidying up
            entry_text: str
            if (entry_text := entry.get("text", None)) is not None:
                new_text = entry_text.replace("\\", "")
                new_text = new_text.replace("\u2028", "\n")
                new_text = new_text.replace("\u1C6A", "\n\n")
                new_text = new_text.replace("\u200b", "")
                # TODO: fix multiple, consecutive newlines as well, e.g., \n\n\n\n -> \n

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
                                verbose_msg(
                                    f"Renaming {original_photo_file} to {renamed_photo_file}"
                                )
                            original_photo_file.rename(renamed_photo_file)

                        new_text = re.sub(
                            r"(\!\[\]\(dayone-moment:\/\/)([A-F0-9]+)\)",
                            (rf"![[\2.{image_type}]]"),
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
                                verbose_msg(
                                    f"Renaming {original_pdf_file} to {renamed_pdf_file}"
                                )
                            original_pdf_file.rename(renamed_pdf_file)

                        new_text = re.sub(
                            r"(\!\[\]\(dayone-moment:\/+pdfAttachment\/)([A-F0-9]+)\)",
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
                                verbose_msg(
                                    f"Renaming {original_audio_file} to {renamed_audio_file}"
                                )
                            original_audio_file.rename(renamed_audio_file)

                        new_text = re.sub(
                            r"(\!\[\]\(dayone-moment:\/+audio/)([A-F0-9]+)\)",
                            rf"![[\2.{audio_format}]]",
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
                                verbose_msg(
                                    f"Renaming {original_video_file} to {renamed_video_file}"
                                )
                            original_video_file.rename(renamed_video_file)

                        new_text = re.sub(
                            r"(\!\[\]\(dayone-moment:\/+video/)([A-F0-9]+)\)",
                            rf"![[\2.{video_format}]]",
                            new_text,
                        )

                new_entry.text = new_text

                # Add the entry's uuid as an hidden section (won't be present in Obsidian preview mode)
                # new_entry.text.append(f"\n\n%%\nuuid:: {new_entry.uuid}\n%%")

            # Save entries organised by year, year-month, year-month-day.md
            year_dir = journal_folder / str(creation_date.year)
            month_dir = year_dir / creation_date.strftime("%Y-%m")
            if not month_dir.is_dir():
                month_dir.mkdir(parents=True)

            # Target filename to save to
            file_date_format = local_date.strftime("%Y-%m-%d")
            target_file = month_dir / f"{file_date_format}.md"
            new_entry.output_file = target_file

            # Relative path, to check if this entry is already present in the vault directory
            target_file_rel = (
                Path(journal_name)
                / f"{creation_date.strftime('%Y/%Y-%m')}" / f"{file_date_format}.md"
            )

            # Skip files already present in the vault directory
            if vault_directory is None or (
                force
                or not (Path(vault_directory).expanduser() / target_file_rel).exists()
            ):
                # Here is where we handle multiple entries on the same day. Each goes to it's own file
                if target_file.stem in entries:
                    if verbose > 1:
                        warn_msg(
                            f"Found another entry with the same date '{target_file.stem}'"
                        )
                    if merge_entries:
                        merged_entries += 1
                        prev_entry: Entry = entries.pop(target_file.stem)
                        del prev_entry.metadata["dates"]
                        new_entry.text += f"\n\n{entries_separator}\n\n{prev_entry}"
                    else:
                        # File exists, need to find the next in sequence and append alpha character marker
                        index = 97  # ASCII a
                        target_file = month_dir / f"{file_date_format}{chr(index)}.md"
                        while target_file.stem in entries:
                            index += 1
                            target_file = (
                                month_dir / f"{file_date_format}{chr(index)}.md"
                            )
                        new_entry.output_file = target_file

                # Add current entry's as a new key-value pair in entries dict
                entries[target_file.stem] = new_entry

                # Step 1 to replace dayone internal links to other entries with proper Obsidian [[links]]
                uuid_to_file[new_entry.uuid] = target_file.name
            else:
                if verbose > 1:
                    verbose_msg(
                        f"File '{target_file_rel}' already exists in vault directory!"
                    )

            progress.update(task, advance=1)

    # Rename JSON file to avoid reprocessing if the script is run twice
    num_files = len(list(base_folder.glob(f"*{journal.stem}.json")))
    journal.rename(str(num_files - 1) + "_" + journal.name)

    def replace_link(match: re.Match) -> str:
        """A replacement function for dayone internal links"""
        link_text, uuid = match.groups()
        if uuid in uuid_to_file:
            return f"[[{uuid_to_file[uuid]}|{link_text}]]"
        return f"^[Linked entry with UUID `{uuid}` not found]"

    entry: Entry
    for entry in entries.values():
        if convert_links:
            # Step 2 to replace dayone internal links: we must do a second iteration over entries
            # The regex to match a dayone internal link: [link_text](dayone://view?EntryId=uuid)
            entry.text = re.sub(
                r"\[(.*?)\]\(dayone2?:\/\/.*?([A-F0-9]+)\)", replace_link, entry.text
            )
        entry.dump()

    info_msg(
        f":white_check_mark: {len(entries)}/{len(data['entries'])}{f' ({merged_entries} merged)' if merge_entries else ''} entries have been exported to '{journal_folder}'"
    )
