"""
Technique widget: the dropdowns corresponding to each parameters are generated dynamically.
"""

from typing import Literal, get_args, get_origin

import ipywidgets as ipw
from pydantic.types import NonNegativeFloat, NonNegativeInt

from aurora.schemas.cycling import CyclingParameter, ElectroChemPayloads

# NOTE: requirements of parameters is not enforced when assigning

CHECKBOX_STYLE = {'description_width': '5px'}
CHECKBOX_LAYOUT = {'width': '8%'}
BOX_STYLE = {'description_width': 'initial'}


def build_parameter_widget(param_obj):

    if not isinstance(param_obj, CyclingParameter):
        raise TypeError(
            f"param_obj should be a CyclingParameter instance, not {type(param_obj)}"
        )

    w_check = ipw.Checkbox(
        value=param_obj.required or (param_obj.value is not None),
        disabled=param_obj.required,
        description='',
        style=CHECKBOX_STYLE,
        layout=CHECKBOX_LAYOUT,
    )

    # read the value of parameter. If None, take use the default value
    param_value = param_obj.value if param_obj.value is not None else param_obj.default_value
    value_type = param_obj.__annotations__['value']

    # since 'value' is `Optional`, all values are unions of their
    # actual type and `NoneType`. Here we discard `NoneType`.
    types = tuple(t for t in get_args(value_type) if t != type(None))  # noqa

    if len(types) > 1:
        # Optional[Union] case
        # choose generic str by default
        if str in types:
            value_type = str
            param_value = str(param_value)
        else:
            raise NotImplementedError()
    else:
        # Optional[all-other-types] case
        # pick actual type
        value_type = types[0]

    if get_origin(value_type) is Literal:
        w_param = ipw.Dropdown(description=param_obj.label,
                               placeholder=param_obj.description,
                               options=get_args(value_type),
                               value=param_value,
                               style=BOX_STYLE)
    elif issubclass(value_type, bool):
        w_param = ipw.Dropdown(description=param_obj.label,
                               placeholder=param_obj.description,
                               options=[('False', False), ('True', True)],
                               value=param_value,
                               style=BOX_STYLE)
    elif issubclass(value_type, float):
        if value_type in [NonNegativeFloat]:
            value_min, value_max = (0., 1.e99)
        else:
            value_min, value_max = (-1.e99, 1.e99)
        w_param = ipw.BoundedFloatText(
            description=param_obj.label,
            min=value_min,
            max=value_max,  # step=param_dic.get('step'),
            value=param_value,
            style=BOX_STYLE)
    elif issubclass(value_type, int):
        if value_type in [NonNegativeInt]:
            value_min, value_max = (0, 1e99)
        else:
            value_min, value_max = (-1e99, 1e99)
        w_param = ipw.BoundedIntText(
            description=param_obj.label,
            min=value_min,
            max=value_max,  # step=param_dic.get('step'),
            value=param_value,
            style=BOX_STYLE)
    elif issubclass(value_type, str):
        w_param = ipw.Text(description=param_obj.label,
                           placeholder='',
                           value=param_value,
                           style=BOX_STYLE)
    else:
        raise NotImplementedError()

    def enable_w_param(change=None):
        w_param.disabled = not (w_check.value)

    enable_w_param()
    w_check.observe(enable_w_param, names='value')
    w_units = ipw.HTMLMath(
        f"{param_obj.units}&nbsp&nbsp&nbsp (<i>{param_obj.description}</i>)"
        if param_obj.description else "")

    return ipw.HBox([w_check, w_param, w_units])


class TechniqueParametersWidget(ipw.VBox):

    def __init__(self, technique, **kwargs):
        # technique is an instance of one of the classes in ElecElectroChemPayloads
        if not isinstance(technique, get_args(ElectroChemPayloads)):
            raise ValueError("Invalid technique")

        self.tech_short_name = technique.short_name
        self.tech_description = technique.description

        self.w_name = ipw.Text(description="Step label:",
                               placeholder="Enter a custom name",
                               value=technique.name)
        # layout=self.BOX_LAYOUT, style=self.BOX_STYLE)
        device_options = get_args(technique.__annotations__['device'])
        self.w_device = ipw.Dropdown(description="Device:",
                                     options=device_options,
                                     value=device_options[0],
                                     style=BOX_STYLE)
        self.w_tech_label = ipw.HTML(
            f"<b>Technique:</b> <i>{self.tech_description}</i>")
        self.tech_parameters_names = []
        w_parameters_children = []
        for pname, pobj in technique.parameters.items(
        ):  # loop over parameters
            self.tech_parameters_names.append(pname)
            w_parameters_children.append(build_parameter_widget(pobj))
        self.w_tech_parameters = ipw.VBox(w_parameters_children)

        super().__init__(**kwargs)
        self.children = [
            ipw.HBox([self.w_name, self.w_device]),
            self.w_tech_label,
            self.w_tech_parameters,
        ]

    @property
    def tech_name(self):
        return self.w_name.value

    @property
    def tech_parameters_values(self):
        """Return list of parameters values. If a parameter is disabled, its value will be None."""
        return [(w.children[1].value if w.children[0].value else None)
                for w in self.w_tech_parameters.children]

    @property
    def selected_tech_parameters(self):
        return {
            pname: pvalue
            for pname, pvalue in zip(self.tech_parameters_names,
                                     self.tech_parameters_values)
            if pvalue is not None
        }
