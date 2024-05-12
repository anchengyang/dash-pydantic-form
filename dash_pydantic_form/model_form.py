import contextlib
import itertools
from functools import partial
from typing import Any, Literal

import dash_mantine_components as dmc
from dash import ALL, MATCH, ClientsideFunction, Input, Output, State, clientside_callback, dcc, html
from dash.development.base_component import Component
from dash_iconify import DashIconify
from pydantic import BaseModel

from . import ids as common_ids
from .form_section import Sections
from .utils import deep_merge, get_non_null_annotation, get_subitem_cls


def form_base_id(part: str, aio_id: str, form_id: str):
    """Form parts id."""
    return {"part": part, "aio_id": aio_id, "form_id": form_id}


SectionRender = Literal["accordion", "tabs", "steps"]
Position = Literal["top", "bottom", "none"]


class ModelForm(html.Div):
    """Model form."""

    class ids:
        """Model form ids."""

        main = partial(form_base_id, "_pydantic-form-main")
        accordion = partial(form_base_id, "_pydantic-form-accordion")
        tabs = partial(form_base_id, "_pydantic-form-tabs")
        steps = partial(form_base_id, "_pydantic-form-steps")
        steps_save = partial(form_base_id, "_pydantic-form-steps-save")
        steps_next = partial(form_base_id, "_pydantic-form-steps-next")
        steps_previous = partial(form_base_id, "_pydantic-form-steps-previous")
        steps_nsteps = partial(form_base_id, "_pydantic-form-steps-nsteps")

    def __init__(  # noqa: PLR0912, PLR0913
        self,
        item: BaseModel | type[BaseModel],
        aio_id: str,
        form_id: str,
        path: str = "",
        fields_repr: dict[str, Any] | None = None,
        sections: Sections | None = None,
    ) -> None:
        from dash_pydantic_form.fields import get_default_repr

        with contextlib.suppress(Exception):
            if issubclass(item, BaseModel):
                item = item.model_construct()

        fields_repr = fields_repr or {}
        field_inputs = {}
        subitem_cls = get_subitem_cls(item.__class__, path)
        for field_name, field_info in subitem_cls.model_fields.items():
            if sections and field_name in sections.excluded_fields:
                continue
            if field_name in fields_repr:
                field_repr = fields_repr[field_name]
            else:
                annotation = get_non_null_annotation(field_info.annotation)
                field_repr = get_default_repr(annotation)

            field_inputs[field_name] = field_repr.render(
                item=item,
                aio_id=aio_id,
                form_id=form_id,
                field=field_name,
                parent=path,
                field_info=field_info,
            )

        if not sections:
            children = [self.grid(list(field_inputs.values()))]
        else:
            fields_not_in_sections = set(field_inputs) - set(
                itertools.chain.from_iterable(s.fields for s in sections.sections)
            )

            if sections.render == "accordion":
                render_function = self.render_accordion_sections
            elif sections.render == "tabs":
                render_function = self.render_tabs_sections
            elif sections.render == "steps":
                render_function = self.render_steps_sections
            else:
                raise ValueError("Only 'accordion', 'tabs' and 'steps' are supported for `section_render_type`.")

            sections_render = render_function(
                aio_id=aio_id,
                form_id=form_id,
                field_inputs=field_inputs,
                sections=sections,
                **sections.render_kwargs,
            )

            if sections.remaining_fields_position == "none" or not fields_not_in_sections:
                children = sections_render
            elif sections.remaining_fields_position == "top":
                children = [
                    self.grid([v for k, v in field_inputs.items() if k in fields_not_in_sections], mb="sm")
                ] + sections_render
            else:
                children = sections_render + [
                    self.grid([v for k, v in field_inputs.items() if k in fields_not_in_sections], mb="sm")
                ]

        if not path:
            children.append(dcc.Store(id=self.ids.main(aio_id, form_id)))

        super().__init__(children=children)

    @classmethod
    def grid(cls, children, **kwargs):
        """Create the responsive grid for a field."""
        return dmc.SimpleGrid(children, cols={"base": 1, "sm": 4}, className="pydantic-form-grid", **kwargs)

    @classmethod
    def render_accordion_sections(
        cls,
        *,
        aio_id: str,
        form_id: str,
        field_inputs: dict[str, Component],
        sections: Sections,
        **_kwargs,
    ):
        """Render the form sections as accordion."""
        return [
            dmc.Accordion(
                [
                    dmc.AccordionItem(
                        [
                            dmc.AccordionControl(
                                dmc.Text(
                                    ([DashIconify(icon=section.icon)] if section.icon else []) + [section.name],
                                    style={"display": "flex", "alignItems": "center", "gap": "0.5rem"},
                                    fw=600,
                                ),
                            ),
                            dmc.AccordionPanel(
                                cls.grid([field_inputs[field] for field in section.fields if field in field_inputs]),
                            ),
                        ],
                        value=section.name,
                    )
                    for section in sections.sections
                ],
                value=[section.name for section in sections.sections if section.default_open],
                styles={
                    "control": {"padding": "0.5rem"},
                    "label": {"padding": 0},
                    "item": {
                        "border": "1px solid color-mix(in srgb, var(--mantine-color-gray-light), transparent 40%)",
                        "background": "color-mix(in srgb, var(--mantine-color-gray-light), transparent 80%)",
                        "marginBottom": "0.5rem",
                        "borderRadius": "0.25rem",
                    },
                    "content": {
                        "display": "flex",
                        "flexDirection": "column",
                        "gap": "0.375rem",
                        "padding": "0.125rem 0.5rem 0.5rem",
                    },
                },
                id=cls.ids.accordion(aio_id, form_id),
                multiple=True,
            )
        ]

    @classmethod
    def render_tabs_sections(
        cls,
        *,
        aio_id: str,
        form_id: str,
        field_inputs: dict[str, Component],
        sections: Sections,
        **_kwargs,
    ):
        """Render the form sections as tabs."""
        value = sections.sections[0].name
        for section in sections.sections:
            if section.default_open:
                value = section.name
                break

        return [
            dmc.Tabs(
                [
                    dmc.TabsList(
                        [
                            dmc.TabsTab(
                                dmc.Text(
                                    ([DashIconify(icon=section.icon)] if section.icon else []) + [section.name],
                                    style={"display": "flex", "alignItems": "center", "gap": "0.5rem"},
                                ),
                                value=section.name,
                            )
                            for section in sections.sections
                        ]
                    ),
                    *[
                        dmc.TabsPanel(
                            cls.grid([field_inputs[field] for field in section.fields if field in field_inputs]),
                            value=section.name,
                        )
                        for section in sections.sections
                    ],
                ],
                value=value,
                styles={
                    "panel": {"padding": "1rem 0.5rem 0"},
                },
                id=cls.ids.tabs(aio_id, form_id),
            )
        ]

    @classmethod
    def render_steps_sections(
        cls,
        *,
        aio_id: str,
        form_id: str,
        field_inputs: dict[str, Component],
        sections: Sections,
        **kwargs,
    ):
        """Render the form sections as steps."""
        stepper_styles = deep_merge(
            {
                "root": {"display": "flex", "gap": "1.5rem", "padding": "0.75rem 0 2rem"},
                "content": {"flex": 1, "padding": 0},
                "steps": {"minWidth": 180},
                "step": {"cursor": "pointer"},
                "stepBody": {"padding-top": "0.625rem"},
                "stepCompletedIcon": {"&>svg": {"width": 12}},
            },
            kwargs.get("styles", {}),
        )
        stepper = dmc.Stepper(
            id=cls.ids.steps(aio_id, form_id),
            active=0,
            orientation="vertical",
            size="sm",
            styles=stepper_styles,
            children=[
                dmc.StepperStep(
                    label=section.name,
                    icon=DashIconify(icon=section.icon) if section.icon else None,
                    children=cls.grid([field_inputs[field] for field in section.fields if field in field_inputs]),
                )
                for section in sections.sections
            ]
            + [
                dmc.StepperStep(
                    label="Save",
                    icon=DashIconify(icon="carbon:save", height=14),
                    children=dmc.Stack(
                        [
                            dmc.Text("All done!"),
                            dmc.Button(
                                "Save",
                                id=cls.ids.steps_save(aio_id, form_id),
                                leftSection=DashIconify(icon="carbon:save", height=16),
                            ),
                        ],
                        style={"height": "100%"},
                        align="center",
                        justify="center",
                    ),
                ),
            ],
        )

        return [
            html.Div(
                [
                    stepper,
                    dmc.Group(
                        [
                            dmc.Button(
                                "Back",
                                id=cls.ids.steps_previous(aio_id, form_id),
                                disabled=True,
                                size="compact-md",
                                leftSection=DashIconify(icon="carbon:arrow-left", height=16),
                            ),
                            dmc.Button(
                                "Next",
                                id=cls.ids.steps_next(aio_id, form_id),
                                size="compact-md",
                                rightSection=DashIconify(icon="carbon:arrow-right", height=16),
                            ),
                        ],
                        style={
                            "position": "absolute",
                            "top": f"calc({70 * (len(sections.sections) + 1) - 5}px + 1rem)",
                        },
                    ),
                    dcc.Store(data=len(sections.sections), id=cls.ids.steps_nsteps(aio_id, form_id)),
                ],
                style={"position": "relative"},
            )
        ]


clientside_callback(
    """(_t1, _t2, active, nSteps) => {
        const trigger = dash_clientside.callback_context.triggered
        if (!trigger || trigger.length === 0) return dash_clientside.no_update
        const trigger_id = JSON.parse(trigger[0].prop_id.split(".")[0])
        if (trigger_id.part.includes("next")) return Math.min(active + 1, nSteps)
        if (trigger_id.part.includes("previous")) return Math.max(0, active - 1)
        return dash_clientside.no_update
    }""",
    Output(ModelForm.ids.steps(MATCH, MATCH), "active"),
    Input(ModelForm.ids.steps_previous(MATCH, MATCH), "n_clicks"),
    Input(ModelForm.ids.steps_next(MATCH, MATCH), "n_clicks"),
    State(ModelForm.ids.steps(MATCH, MATCH), "active"),
    State(ModelForm.ids.steps_nsteps(MATCH, MATCH), "data"),
    prevent_inital_call=True,
)

clientside_callback(
    """(active, nSteps) => [active === 0, active === nSteps]""",
    Output(ModelForm.ids.steps_previous(MATCH, MATCH), "disabled"),
    Output(ModelForm.ids.steps_next(MATCH, MATCH), "disabled"),
    Input(ModelForm.ids.steps(MATCH, MATCH), "active"),
    State(ModelForm.ids.steps_nsteps(MATCH, MATCH), "data"),
)

clientside_callback(
    """(id) => {
    const strId = JSON.stringify(id, Object.keys(id).sort())
    const steps = document.getElementById(strId).children[0].children
    for (let i = 0; i < steps.length; i++) {
        const child = steps[i]
        child.addEventListener("click", event => {
            dash_clientside.set_props(id, {active: i})
        })
    }

    return dash_clientside.no_update
    }""",
    Output(ModelForm.ids.steps(MATCH, MATCH), "id"),
    Input(ModelForm.ids.steps(MATCH, MATCH), "id"),
)

clientside_callback(
    ClientsideFunction(namespace="pydf", function_name="getValues"),
    Output(ModelForm.ids.main(MATCH, MATCH), "data"),
    Input(common_ids.value_field(MATCH, MATCH, ALL, ALL), "value"),
    Input(common_ids.checked_field(MATCH, MATCH, ALL, ALL), "checked"),
)