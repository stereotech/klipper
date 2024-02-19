# [wizard]

This object creates a manager that specifies all the steps that will be performed during execution.

## configure

```
[wizard <wizard_name>]
image: /path/to/image/wizard/<wizard_name>
    path to wizard image
type: 3d, 5d, any
    type the modules supported this wizard
steps: step_1, step_2
    list the all steps for current wizard will be used
variable_<name_var>: 1
variable_<name_var>: 2
    the wizard variables
```

## status

```
{'current_step': current wizard_step,
'enabled': 1/0,
'error': error_string,
'variables': variables,
'name': <wizard_name>,
'steps': steps,
'type': type}
```

## commands

#### SET_WIZARD_ENABLE

`SET_WIZARD_ENABLE WIZARD=<wizard_name> ENABLE=<1/0> ERROR=<string_error>`: This command using for change the wizard state to the enable or disable. If need can set the error message.

#### RESET_WIZARD

`RESET_WIZARD WIZARD=<wizard_name>`: The command reset current step to first and set set the wizard to the disabled.

#### SET_WIZARD_STEP

`SET_WIZARD_STEP WIZARD=<wizard_name`>: Set the step to wizard.

#### SET_WIZARD_VARIABLE

`SET_WIZARD_STEP WIZARD=<wizard_name>`: Set the value to the wizard variables

# [wizard_step]

This is the base object that implements the template for creating the rest of the wizard steps.

## configure

```
[wizard_step <wizard_step_name>]
image: path/to/image/wizard/<wizard_step_name>
    path to wizard_step image
landscape: false
    set True if this wizard_step can supported horizontal rendering
description: description_string
    description for this wizard_step, this description the client will be rendered
warning: warning_string
    warning msg for this wizard_step, this msg the client will be rendered
countdown: 0
    time until the end of the wizard
info: info_string
    info about <wizard_step_name>
placeholder: <name_placeholder_component>
   placeholder component name
action_gcode:
    write gcode which will be running if send the cmd [EXECUTE_WIZARD_STEP]
cancel_gcode:
    write gcode which will be running if send the cmd [CANCEL_WIZARD_STEP]
```

## status

```
{'loading':loading,
'placeholder': placeholder}
```

## commands

#### EXECUTE_WIZARD_STEP

`EXECUTE_WIZARD_STEP WIZARD=<wizard_name> STEP=<wizard_step_name>`: Run gcode in the 'action_gcode' option

#### CANCEL_WIZARD_STEP

`CANCEL_WIZARD_STEP WIZARD=<wizard_name> STEP=<wizard_step_name>`: Run gcode in the 'cancel_gcode' option

#### WIZARD_STEP_LOADING_STATE

`WIZARD_STEP_LOADING_STATE WIZARD=<wizard_name> STEP=<wizard_step_name> ENABLE=<1/0>`: Change state for show the placeholder, enable/disable loading state.

# [wizard_step_wizards]

this step allows you to display all the managers that can be performed in this step. (step to select a manager)

## configure

```
[wizard_step_wizards <wizard_step_name>]
! Note all options of the [wizard_step] object are supported
wizards: wizard1, wizard2
    list the all wizards for current step
```

## status

such as [wizard_step]

## commands

! Note all cmd of the [wizard_step] object are supported

# [wizard_step_tree]

step for support  component the data-selector (material-selector), which  send json to client and client can rendering items

## configure

```
[wizard_step_tree <wizard_step_name>]
! Note all options of the [wizard_step] object are supported
tree_file_path: ./path/to/data.json
    path to data.json
depth: 3
    depth tree, for client can rendering items
types: manufacturer, series, name
    name for everyone node, for client can rendering items
```

## status

```
{
    'tree': tree,
    'selected': selected,
    'value': value
}
 ```

## commands

! Note all cmd of the [wizard_step] object are supported

#### WIZARD_STEP_TREE

`WIZARD_STEP_TREE WIZARD=<wizard_name> STEP=STEP_TREE_1 KEY=pla`: select key from tree for set the value

# [wizard_step_slider]

Step for support component slider. You can specify the required number of sliders for which this object will change its value and interact with the client. Note: by the number of sliders, the client understands how much to draw

## configure

```
[wizard_step_slider <wizard_step_name>]
! Note all options of the [wizard_step] object are supported
slider_<slider_name>_min: 0
slider_<slider_name>_max: 100
slider_<slider_name>_step: 1
slider_<slider_name>_default: 20
    slider data for used to klipper and for for client can rendering it. Can set more sliders

...

```

## status

```
{
    <slider_name1>: current_value,
    <slider_name2>: current_value,
    ...
}
 ```

## commands

! Note all cmd of the [wizard_step] object are supported

#### WIZARD_STEP_TREE

`WIZARD_STEP_SLIDER WIZARD=<wizard_name> STEP=<wizard_step_name> SLIDER=<slider_name2> VALUE=<value>`: update the value for the selected slider..

# [wizard_step_selector]

Step for support component selector.

## configure

```
[wizard_step_selector <wizard_step_name>]
! Note all options of the [wizard_step] object are supported
items: <item_name>, <item_name>, ...
    list items which can select, client get info from this row for rendering items. You can specify the required number of item
select_gcode:
    write gcode which will be running if send the cmd [WIZARD_STEP_SELECT]
...

```

## status

```
{
    'selected': <selected_item>
}
 ```

## commands

! Note all cmd of the [wizard_step] object are supported

#### WIZARD_STEP_SELECT

`WIZARD_STEP_SELECT WIZARD=<wizard_name> STEP=<wizard_step_name> ITEM=<item>`: Run gcode in the 'select_gcode' section.

# [wizard_step_nozzle_offset]

This step is used for the nozzle_offset manager, it specifies all the necessary data for rendering and operation of the klipper application

## configure

```
[wizard_step_selector <wizard_step_name>]
! Note all options of the [wizard_step] object are supported
steps: 15
    the number of steps so that the application can work with this data and the client can draw it
default_step: 7
    the step number so that the application can work with this data and the client can draw it
step_value: 0.1
    the step value so that the client can work with this data
min_value: -0.7
    the minimal value so that the client can work with this data
```

## status

```
{
    'step_x': step_x,
    'step_y': step_y,
}
 ```

## commands

! Note all cmd of the [wizard_step] object are supported

#### WIZARD_STEP_NOZZLE_OFFSET

`WIZARD_STEP_NOZZLE_OFFSET WIZARD=<wizard_name> STEP=<wizard_step_name> STEP_X=<value> STEP_Y=<value>`: set current step for axis X or Y. This command is used to move along the calibration ruler (vernier scale)

# [wizard_step_jog]

Using this step, you can control the axes of the printer, as well as the data from this step is used by the client for rendering

## configure

```
[wizard_step_jog <wizard_step_name>]
! Note all options of the [wizard_step] object are supported

axes: x, y, z, a, c
    axes that can be controlled. The client uses this information to display
steps: 0.1, 1, 10, 20
    values for steps, client uses this information to display
default_step: 10
    the default value with which movements will occur for a given axis
jog_gcode:
    write gcode which will be running if send the cmd [WIZARD_STEP_JOG]

```

## status

```
{
    'loading':loading,
    'placeholder': placeholder
    'step': default_step
    }
```

## commands

! Note all cmd of the [wizard_step] object are supported

#### WIZARD_STEP_SET_STEP

`WIZARD_STEP_SET_STEP WIZARD=<wizard_name> STEP=<wizard_step_name> VALUE=<value>`: Set step for moving the axis

#### WIZARD_STEP_JOG

`WIZARD_STEP_JOG WIZARD=<wizard_name> STEP=<wizard_step_name> AXIS=<axis_name> DIRECTION=<1/0>`: Perform axis movement

# [wizard_step_button]

A step to port the button component, with which you can respond to button clicks. You can specify the required number of buttons. Data on the name and number of buttons are read from the configuration.

## configure

```
[wizard_step_button <wizard_step_name>]
! Note all options of the [wizard_step] object are supported

button_<button_name>_gcode:
    write gcode which will be running if send the cmd [WIZARD_STEP_BUTTON]
button_<button_name>_loadingtime:
    the delay about press button, default 0.0

```

## status

```
{
    'loading':loading,
    'placeholder': placeholder
    }
```

## commands

! Note all cmd of the [wizard_step] object are supported

#### WIZARD_STEP_BUTTON

`WIZARD_STEP_BUTTON WIZARD=<wizard_name> STEP=<wizard_step_name> BUTTON=<button_name>`: Run gcode in the 'button_%s_gcode' section
