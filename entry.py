"""A class to reprensent a DayOne entry"""

from attrs import define, field
from pathlib import Path
import pytz
import dateutil
import datetime


@define
class Entry:
    """A class to represent a DayOne journal entry"""

    uuid: str = field(default=None, eq=True)
    creation_date: datetime.datetime = field(default=None, eq=False)
    has_yaml: bool = field(default=False, eq=False)
    yaml: str = field(default="", eq=False)
    metadata: dict = field(factory=dict, eq=False)
    text: str = field(default="", eq=False)
    output_file: Path = field(default=None, eq=False)

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

        metadata = [f"{key}:: {value}" for key, value in self.metadata.items()]

        return "{yaml}{metadata}\n\n{text}\n".format(
            yaml=self.yaml, metadata="\n".join(metadata), text=self.text, uuid=self.uuid
        )

    def __retreive_metadata(self, entry: dict, **kwargs) -> None:
        """Retreive and set metadata from a JSON entry"""
        # Date and (local) time
        local_date = self.creation_date.astimezone(pytz.timezone(entry["timeZone"]))
        self.metadata["dates"] = local_date.strftime("%Y-%m-%d")
        self.metadata["time"] = local_date.strftime("%H:%M:%S")

        # Place and GPS location
        # TODO: should we print a warning (if verbose mode) when an entry doens't have a location?
        if (entry_location := entry.get("location")) is not None:
            places = []
            for key in ("placeName", "localityName", "administrativeArea", "country"):
                if (place := entry_location.get(key)) is not None:
                    places.append(place)

            self.metadata["places"] = ", ".join(places)

            if "latitude" in entry_location and "longitude" in entry_location:
                self.metadata[
                    "location"
                ] = f"{entry_location.get('latitude')}, {entry_location.get('longitude')}"

        # Weather info
        if "weather" in entry and all(
            info in entry["weather"]
            for info in ["conditionsDescription", "temperatureCelsius", "windSpeedKPH"]
        ):
            weather = entry["weather"]
            self.metadata["weather"] = f"{weather['conditionsDescription']}, "
            f"{round(weather['temperatureCelsius'], 1)}°C, "
            f"{round(weather['windSpeedKPH'], 1)} km/h wind"

        # TODO: Tags

    @classmethod
    def from_json_entry(cls, json_entry: dict, **kwargs) -> "Entry":
        """Create a new `Entry` from a DayOne JSON entry"""
        # Get entry's UUID and the creation date
        uuid = json_entry.get("uuid")
        creation_date = dateutil.parser.isoparse(json_entry.get("creationDate"))
        # Initialize the new entry
        entry = cls(uuid=uuid, creation_date=creation_date)
        # Retreive entry's metadata
        entry.__retreive_metadata(json_entry, **kwargs)

        return entry

    # TODO: to remove
    @classmethod
    def from_metadata(cls, metadata: dict) -> "Entry":
        """Create a new `Entry` from a metadata dictionary"""
        if not isinstance(metadata, dict):
            raise TypeError(
                f"Metadata must be of `dict` type, instead of {type(metadata)}."
            )

        entry = cls(uuid=metadata.pop("uuid", None), metadata=metadata)

        if entry.uuid is not None:
            entry.metadata["url"] = f"[DayOne](dayone://view?entryId={entry.uuid})"

        return entry

    def dump(self) -> None:
        """Dump entry to a file"""
        if self.output_file is None:
            raise RuntimeError("Entry output file is undefined!")
        with self.output_file.open("w", encoding="utf-8") as file:
            file.write(f"{self}")
