"""A class to reprensent a DayOne entry"""

import datetime
from pathlib import Path
from string import whitespace
from typing import Any, Union

import pytz
from attrs import define, field
from dateutil.parser import isoparse


def capwords(string: str, sep: str = "") -> str:
    """Capitalize the first letter of each word in a string"""
    return sep.join(word[0].upper() + word[1:].lower() for word in string.split(" "))


def quote(value: Any) -> Union[Any, str]:
    """Quote if `value` is a string containing whitespaces"""
    if isinstance(value, str) and any(c in value for c in whitespace):
        return '"{}"'.format(value)
    return value


@define
class Entry:
    """A class to represent a DayOne journal entry"""

    uuid: str = field(default=None, eq=True)
    creation_date: datetime.datetime = field(default=None, eq=False)
    local_date: datetime.datetime = field(default=None, eq=False)
    has_yaml: bool = field(default=False, eq=False)
    yaml_fields: list = field(
        factory=list, eq=False, converter=lambda x: list(map(str.lower, x))
    )
    yaml: str = field(default="", eq=False)
    metadata: dict = field(factory=dict, eq=False)
    text: str = field(default="", eq=False)
    output_file: Path = field(default=None, eq=False)

    def __str__(self) -> str:
        if self.has_yaml:
            self.yaml = "---\n{yaml_block}\n---\n".format(
                yaml_block="\n".join(
                    [
                        f"{name.lower().replace(' ', '-')}: {quote(value)}"
                        for name, value in self.metadata.items()
                        if name in self.yaml_fields
                    ]
                )
            )

        metadata_str = "\n".join(
            [
                f"{key}:: {value}"
                for key, value in self.metadata.items()
                if key not in self.yaml_fields
            ]
        )

        return "{yaml}\n{metadata}\n\n---\n\n{text}\n".format(
            yaml=self.yaml, metadata=metadata_str, text=self.text
        )

    def __retreive_metadata(self, entry: dict, **kwargs: dict) -> None:
        """
        Retreive and set metadata from a JSON entry

        Available metadata fields:
            - created: creation date & time (ISO 8601 format)
            - place: street, city, country
            - lat, lon: GPS coordinates
            - weather: weather conditions
            - journal: journal name
            - favorite: whether the entry is starred
            - url: external link to the entry in Day One
        """
        # Date and (local) time
        self.local_date = self.creation_date.astimezone(
            pytz.timezone(entry["timeZone"])
        )
        self.metadata["created"] = self.local_date.isoformat()

        # Place and GPS location
        if (entry_location := entry.get("location")) is not None:
            places = []
            for key in ("placeName", "localityName", "administrativeArea", "country"):
                if (place := entry_location.get(key)) is not None:
                    places.append(place)

            self.metadata["place"] = ", ".join(places)

            for gps in ("latitude", "longitude"):
                # Save location as "lat" and "lon", if present
                self.metadata[gps[:3]] = entry_location.get(gps, None)

        # Weather info
        if "weather" in entry and all(
            info in entry["weather"]
            for info in ["conditionsDescription", "temperatureCelsius", "windSpeedKPH"]
        ):
            weather = entry["weather"]
            self.metadata["weather"] = (
                f"{weather['conditionsDescription']}, "
                + f"{round(weather['temperatureCelsius'], 1)}°C, "
                + f"{round(weather['windSpeedKPH'], 1)} km/h wind"
            )

        # Add journal name, if present
        if (journal_name := kwargs.get("journal_name")) is not None:
            self.metadata["journal"] = journal_name

        # Tags
        tags = []

        ignore_tags = kwargs.get("ignore_tags") or set()
        status_tags = kwargs.get("status_tags") or set()

        if (entry_tags := entry.get("tags")) is not None:
            entry_tags = set(entry_tags)

            for tag in (entry_tags - set(ignore_tags)) - set(status_tags):
                tags.append(capwords(f"{kwargs.get('tag_prefix')}/{tag}"))

            # Handle status tags
            if status_tags := entry_tags & status_tags:
                tags.extend(
                    map(
                        lambda tag: capwords(f"{kwargs.get('status_prefix')}/{tag}"),
                        status_tags,
                    )
                )

        # Mark favorite entries
        self.metadata["favorite"] = True if entry.get("starred") else False

        # UUID and DayOne URL
        if self.uuid is not None:
            self.metadata["url"] = f"[DayOne](dayone://view?entryId={self.uuid})"

        # Add any entra tags, if present
        if (extra_tags := kwargs.get("extra_tags")) is not None:
            tags.extend(extra_tags)

        # Add tags to metadata, if not empty
        if tags:
            self.metadata["tags"] = ", ".join(tags)

        # Discard ignored fields, if any
        if (ignore_fields := kwargs.get("ignore_fields")) is not None:
            assert isinstance(ignore_fields, list), "ignore_fields must be a list!"
            for key in ignore_fields:
                self.metadata.pop(key, None)

    @classmethod
    def from_json_entry(cls, json_entry: dict, **kwargs) -> "Entry":
        """Create a new `Entry` from a DayOne JSON entry"""
        if not isinstance(json_entry, dict):
            raise TypeError(
                f"Metadata must be of `dict` type, instead of {type(json_entry)}."
            )

        # Get entry's UUID and the creation date
        uuid = json_entry.get("uuid")
        creation_date = isoparse(json_entry.get("creationDate"))
        # Initialize the new entry
        entry = cls(uuid=uuid, creation_date=creation_date)
        # Populate entry's metadata
        entry.__retreive_metadata(json_entry, **kwargs)

        return entry

    def dump(self) -> None:
        """Dump entry to a file"""
        if self.output_file is None:
            raise RuntimeError("Entry output file is undefined!")
        with self.output_file.open("w", encoding="utf-8") as file:
            file.write(f"{self}")
