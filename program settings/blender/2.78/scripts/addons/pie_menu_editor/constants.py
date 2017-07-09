ED_DATA = (
    ('PMENU', "Pie Menu", 'PROP_CON'),
    ('RMENU', "Regular Menu", 'MOD_BOOLEAN'),
    ('DIALOG', "Popup Dialog", 'MOD_BUILD'),
    ('SCRIPT', "Stack Key", 'MOD_SKIN'),
    ('PANEL', "Panel Group", 'MOD_MULTIRES'),
    ('HPANEL', "Hidden Panel Group", 'MOD_WIREFRAME'),
    ('STICKY', "Sticky Key", 'MOD_DATA_TRANSFER'),
    ('MACRO', "Macro Operator", 'MOD_ARRAY'),
)

PM_ITEMS = tuple(
    (id, name, "", icon, i)
    for i, (id, name, icon) in enumerate(ED_DATA)
)

PM_ITEMS_M = tuple(
    (id, name, "", icon, 1 << i)
    for i, (id, name, icon) in enumerate(ED_DATA)
)

PM_ITEMS_M_DEFAULT = set(id for id, name, icon in ED_DATA)

OP_CTX_ITEMS = (
    ('INVOKE_DEFAULT', "Invoke (Default)", "", 'OUTLINER_OB_LAMP', 0),
    ('INVOKE_REGION_WIN', "Invoke Window Region", "", 'OUTLINER_OB_LAMP', 1),
    ('INVOKE_REGION_CHANNELS', "Invoke Channels Region", "",
        'OUTLINER_OB_LAMP', 2),
    ('INVOKE_REGION_PREVIEW', "Invoke Preview Region", "",
        'OUTLINER_OB_LAMP', 3),
    ('INVOKE_AREA', "Invoke Area", "", 'OUTLINER_OB_LAMP', 4),
    ('INVOKE_SCREEN', "Invoke Screen", "", 'OUTLINER_OB_LAMP', 5),
    ('EXEC_DEFAULT', "Exec", "", 'LAMP_DATA', 6),
    ('EXEC_REGION_WIN', "Exec Window Region", "", 'LAMP_DATA', 7),
    ('EXEC_REGION_CHANNELS', "Exec Channels Region", "", 'LAMP_DATA', 8),
    ('EXEC_REGION_PREVIEW', "Exec Preview Region", "", 'LAMP_DATA', 9),
    ('EXEC_AREA', "Exec Area", "", 'LAMP_DATA', 10),
    ('EXEC_SCREEN', "Exec Screen", "", 'LAMP_DATA', 11),
)

ICON_ON = 'CHECKBOX_HLT'
ICON_OFF = 'CHECKBOX_DEHLT'

DEFAULT_POLL = "return True"

NUM_LIST_ROWS = 10
LIST_PADDING = 0.5
SCALE_X = 1.5
SEPARATOR_SCALE_Y = 11 / 18
SPACER_SCALE_Y = 0.3

I_CLIPBOARD = "Clipboard is empty"
I_CMD = "Bad command"
I_DEBUG = "Debug mode: %s"
I_NO_ERRORS = "No errors were found"
W_CMD = "PME: Bad command: %s"
W_FILE = "PME: Bad file"
W_JSON = "PME: Bad json"
W_KEY = "PME: Bad key: %s"
W_PM = "Menu '%s' was not found"
W_PROP = "PME: Bad property: %s"


ARROW_ICONS = ("@p4", "@p6", "@p2", "@p8", "@p7", "@p9", "@p1", "@p3")

SPACE_ITEMS = (
    ('VIEW_3D', "3D View", "", 'VIEW3D', 0),
    ('DOPESHEET_EDITOR', "Dope Sheet", "", 'ACTION', 1),
    ('FILE_BROWSER', "File Browser", "", 'FILESEL', 2),
    ('GRAPH_EDITOR', "Graph Editor", "", 'IPO', 3),
    ('INFO', "Info", "", 'INFO', 4),
    ('LOGIC_EDITOR', "Logic Editor", "", 'LOGIC', 5),
    ('CLIP_EDITOR', "Movie Clip Editor", "", 'CLIP', 6),
    ('NLA_EDITOR', "NLA Editor", "", 'SEQ_SEQUENCER', 7),
    ('NODE_EDITOR', "Node Editor", "", 'NODETREE', 8),
    ('OUTLINER', "Outliner", "", 'OOPS', 9),
    ('PROPERTIES', "Properties", "", 'UI', 10),
    ('CONSOLE', "Python Console", "", 'CONSOLE', 11),
    ('TEXT_EDITOR', "Text Editor", "", 'TEXT', 12),
    ('TIMELINE', "Timeline", "", 'TIME', 13),
    ('USER_PREFERENCES', "User Preferences", "", 'PREFERENCES', 14),
    ('IMAGE_EDITOR', "UV/Image Editor", "", 'IMAGE_COL', 15),
    ('SEQUENCE_EDITOR', "Video Sequence Editor", "", 'SEQUENCE', 16),
)

REGION_ITEMS = (
    ('TOOLS', "Tools", "T-panel", 'PREFERENCES', 0),
    ('UI', "UI", "N-panel", 'SETTINGS', 1),
    ('WINDOW', "Window", "Properties Area", 'BUTS', 2),
    ('HEADER', "Header", "Top or bottom bar", 'FULLSCREEN', 3),
)

OPEN_MODE_ITEMS = (
    ('PRESS', "Press", "Press the key", 'ROTACTIVE', 0),
    ('HOLD', "Hold", "Hold the key", 'ROTATE', 1),
    ('DOUBLE_CLICK', "Double Click", "Double click the key",
        'ROTATECOLLECTION', 2),
    # ('ONE_SHOT', "Press (w/o autorepeat)",
    #     ("Press the key. \n"
    #         "Disable keyboard autorepeat feature"),
    #     'BBOX', 3),
)
