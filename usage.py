import json
from datetime import date
from enum import Enum
from typing import Literal

import dash_mantine_components as dmc
from dash import MATCH, Dash, Input, Output, _dash_renderer, callback, clientside_callback
from dash_iconify import DashIconify
from pydantic import BaseModel, Field, ValidationError

from dash_pydantic_form import FormSection, ModelForm, Sections, fields, ids

_dash_renderer._set_react_version("18.2.0")
app = Dash(
    __name__,
    external_stylesheets=[
        "https://unpkg.com/@mantine/dates@7/styles.css",
        "https://unpkg.com/@mantine/code-highlight@7/styles.css",
        "https://unpkg.com/@mantine/charts@7/styles.css",
        "https://unpkg.com/@mantine/carousel@7/styles.css",
        "https://unpkg.com/@mantine/notifications@7/styles.css",
        "https://unpkg.com/@mantine/nprogress@7/styles.css",
    ],
)

server = app.server


class Office(Enum):
    """Office enum."""

    AU = "au"
    FR = "fr"
    UK = "uk"


class Species(Enum):
    """Species enum."""

    CAT = "cat"
    DOG = "dog"


class Metadata(BaseModel):
    """Metadata model."""

    languages: list[Literal["fr", "en", "sp", "cn"]] = Field(title="Languages spoken", default_factory=list)
    siblings: int | None = Field(title="Siblings", default=None, ge=0)


class Pet(BaseModel):
    """Pet model."""

    name: str = Field(title="Name", description="Name of the pet")
    species: Species = Field(title="Species", description="Species of the pet")
    dob: date | None = Field(title="Date of birth", description="Date of birth of the pet", default=None)
    alive: bool = Field(title="Alive", description="Is the pet alive", default=True)

    def __str__(self) -> str:
        """String representation."""
        return str(self.name)


class HomeOffice(BaseModel):
    """Home office model."""

    type: Literal["home_office"]
    has_workstation: bool = Field(title="Has workstation", description="Does the employee have a suitable workstation")


class WorkOffice(BaseModel):
    """Work office model."""

    type: Literal["work_office"]
    commute_time: int = Field(title="Commute time", description="Commute time in minutes", ge=0)


class Employee(BaseModel):
    """Employee model."""

    name: str = Field(title="Name", description="Name of the employee", min_length=2)
    age: int = Field(title="Age", description="Age of the employee, starting from their birth", ge=18)
    mini_bio: str | None = Field(title="Mini bio", description="Short bio of the employee", default=None)
    joined: date = Field(title="Joined", description="Date when the employee joined the company")
    office: Office = Field(title="Office", description="Office of the employee")
    metadata: Metadata | None = Field(title="Employee metadata", default=None)
    location: HomeOffice | WorkOffice | None = Field(title="Work location", default=None, discriminator="type")
    pets: list[Pet] = Field(title="Pets", description="Employee pets", default_factory=list)
    jobs: list[str] = Field(
        title="Past jobs", description="List of previous jobs the employee has held", default_factory=list
    )


bob = Employee(
    name="Bob",
    age=30,
    joined="2020-01-01",
    mini_bio="### Birth\nSomething something\n\n### Education\nCollege",
    office="au",
    metadata={"languages": ["fr", "en"], "siblings": 2},
    pets=[{"name": "Rex", "species": "cat"}],
    location={
        "type": "home_office",
        "has_workstation": True,
    },
    jobs=["Engineer", "Lawyer"],
)


AIO_ID = "home"
FORM_ID = "Bob"

app.layout = dmc.MantineProvider(
    id="mantine-provider",
    defaultColorScheme="auto",
    children=dmc.AppShell(
        [
            dmc.AppShellMain(
                dmc.Container(
                    [
                        dmc.Group(
                            [
                                dmc.Title("Dash Pydantic form", order=3),
                                dmc.Switch(
                                    offLabel=DashIconify(icon="radix-icons:moon", height=18),
                                    onLabel=DashIconify(icon="radix-icons:sun", height=18),
                                    size="md",
                                    color="yellow",
                                    persistence=True,
                                    checked=True,
                                    id="scheme-switch",
                                ),
                            ],
                            align="center",
                            justify="space-between",
                            mb="1rem",
                        ),
                        ModelForm(
                            # Employee,
                            bob,
                            AIO_ID,
                            FORM_ID,
                            # read_only=True,
                            # submit_on_enter=True,
                            # debounce_inputs=200,
                            fields_repr={
                                "name": {"placeholder": "Enter your name"},
                                "mini_bio": fields.Markdown(),
                                "office": fields.RadioItems(
                                    options_labels={"au": "Australia", "fr": "France"},
                                ),
                                "metadata": {
                                    "render_type": "accordion",
                                    "fields_repr": {
                                        "languages": fields.Checklist(
                                            options_labels={
                                                "fr": "French",
                                                "en": "English",
                                                "sp": "Spanish",
                                                "cn": "Chinese",
                                            },
                                            visible=("_root_:office", "==", "au"),
                                        ),
                                    },
                                },
                                "pets": fields.EditableTable(
                                    fields_repr={
                                        "species": {"options_labels": {"dog": "Dog", "cat": "Cat"}},
                                    },
                                    table_height=200,
                                ),
                                "location": {
                                    "fields_repr": {
                                        "type": fields.RadioItems(
                                            options_labels={"home_office": "Home", "work_office": "Work"}
                                        )
                                    },
                                },
                                "jobs": {"placeholder": "A job name"},
                            },
                            sections=Sections(
                                sections=[
                                    FormSection(name="General", fields=["name", "age", "mini_bio"], default_open=True),
                                    FormSection(
                                        name="HR",
                                        fields=["office", "joined", "location", "metadata"],
                                        default_open=True,
                                    ),
                                    FormSection(name="Other", fields=["pets", "jobs"], default_open=True),
                                ],
                                render="accordion",
                            ),
                        ),
                    ],
                    pt="1rem",
                )
            ),
            dmc.AppShellAside(
                dmc.ScrollArea(
                    dmc.Text(
                        id=ids.form_dependent_id("output", AIO_ID, FORM_ID),
                        style={"whiteSpace": "pre-wrap"},
                        p="1rem 0.5rem",
                    ),
                ),
            ),
        ],
        aside={"width": 350},
    ),
)


@callback(
    Output(ids.form_dependent_id("output", MATCH, MATCH), "children"),
    Output(ModelForm.ids.errors(MATCH, MATCH), "data"),
    Input(ModelForm.ids.main(MATCH, MATCH), "data"),
    prevent_initial_call=True,
)
def display(form_data):
    """Display form data."""
    children = dmc.Stack(
        [
            dmc.Text("Form data", mb="-0.5rem", fw=600),
            dmc.Code(
                json.dumps(form_data, indent=2),
            ),
        ]
    )
    errors = None
    try:
        Employee.model_validate(form_data)
    except ValidationError as e:
        children.children.extend(
            [
                dmc.Text("Validation errors", mb="-0.5rem", fw=500, c="red"),
                dmc.List(
                    [
                        dmc.ListItem(
                            [".".join([str(x) for x in error["loc"]]), f" : {error['msg']}, got {error['input']}"],
                        )
                        for error in e.errors()
                    ],
                    size="sm",
                    c="red",
                ),
            ]
        )
        errors = None
        errors = {":".join([str(x) for x in error["loc"]]): error["msg"] for error in e.errors()}

    return children, errors


clientside_callback(
    """(isLightMode) => isLightMode ? 'light' : 'dark'""",
    Output("mantine-provider", "forceColorScheme"),
    Input("scheme-switch", "checked"),
    prevent_initial_callback=True,
)


if __name__ == "__main__":
    app.run_server(debug=True)
