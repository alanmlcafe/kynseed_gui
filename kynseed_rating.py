from items import ITEM_DICT
from lists import (
    TOOL_QUALITY_LIST,
    FOLLOWER_LIST,
    GATHER_TYPE_LIST,
    WEATHER_LIST,
    TRAIT_LIST,
    SEASON_LIST,
    TIME_LIST,
    OPTION_MENU,
)
import tkinter as tk
import customtkinter as ctk
from fuzzywuzzy import fuzz
from PIL import Image
from copy import deepcopy
from io import BytesIO
import subprocess
import re

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")

def separate_pascal_case(string: str) -> str:
    """
    Separate a pascal case string into words.
    Example:
        separate_pascal_case("PascalCase") -> "Pascal Case"

    Args:
        string (str): Pascal case string

    Returns:
        str: Separated string
    """
    return ' '.join(re.findall(r'[A-Z][^A-Z]*', string))

def dwebp(file: str) -> Image:
    """
    Convert a webp file to a PIL Image.
    Args:
        file (str): Path to webp file

    Raises:
        Exception: If dwebp fails

    Returns:
        _type_: PIL Image
    """
    webp = subprocess.run(f"dwebp {file} -quiet -o -", shell=True, capture_output=True)
    if webp.returncode != 0:
        raise Exception(webp.stderr.decode())
    else:
        return Image.open(BytesIO(webp.stdout))


def average_rgb(image: Image) -> tuple:
    """
    Get the average RGBA of an image.

    Args:
        image (Image): PIL Image

    Returns:
        tuple[float, float, float]: Average RGB
    """
    ### Remove transparent
    rgba_list = []
    for h in range(image.height):
        for w in range(image.width):
            var = image.getpixel((w, h))
            if var[3] != 0:
                rgba_list.append(var)

    ### Get average RGBA
    r_total = 0
    g_total = 0
    b_total = 0
    a_total = 0
    for rgba in rgba_list:
        r_total += rgba[0]
        g_total += rgba[1]
        b_total += rgba[2]
        a_total += rgba[3]
    length = len(rgba_list)
    
    if length == 0:
        return None
    
    ### Return just the RGB
    return round(r_total / length), round(g_total / length), round(b_total / length)


def rgb_to_hex(rgb: tuple) -> str:
    """
    Convert an RGB tuple to a hex string.

    Args:
        rgb (tuple[int, int, int]): RGB tuple
    
    Returns:
        str: Hex string
    """
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def complementary_color(my_hex: str) -> str:
    """
    Get the complementary color of a hex string.

    Args:
        my_hex (str): Hex string
    
    Returns:
        str: Complementary hex string
    """
    if my_hex[0] == "#":
        my_hex = my_hex[1:]
    rgb = (my_hex[0:2], my_hex[2:4], my_hex[4:6])
    comp = ["%02X" % (255 - int(a, 16)) for a in rgb]
    return "#" + "".join(comp)


class App(ctk.CTk):
    def __init__(self):
        """
        Initialize the App.

        Args:
            ctk (ctk.CTk): Custom Tkinter
        
        Returns:
            None
        """
        super().__init__()

        ### Set the window size
        self.geometry("1200x620")
        self.title("Kynseed Rating")
        self.minsize(1200, 620)

        ### List to store that will be displayed
        self.dict_display = {}
        self.list_display_labels = []

        ### Create a grid system
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure((0, 1), weight=1)

        ### Frame for the Filters
        self.filter_frame = ctk.CTkFrame(self, width=120, height=580)
        self.filter_frame.grid(
            row=0, column=5, padx=(20, 20), pady=(20, 20), sticky="nsew"
        )

        ### Create the image icons
        self.reverse_icon = ctk.CTkImage(
            Image.open("images/reverse.png"), size=(20, 20)
        )

        ### Filter title
        self.filter_title = ctk.CTkLabel(
            self.filter_frame, text="Filter", font=ctk.CTkFont(size=20, weight="bold")
        )
        self.filter_title.grid(row=0, column=0, padx=10, pady=(10, 10))
        ### full_reverse_filters
        reverse = ctk.CTkButton(
            master=self.filter_frame,
            text="",
            image=self.reverse_icon,
            command=self.full_reverse_filters,
            width=20,
            height=20,
        )

        ### cache for colors
        self.color_cache = {}

        reverse.grid(row=0, column=1, padx=5, pady=(10, 10))

        self.filter_iterable = 1

        ### filter dict
        self.dict_filter = {
            "gatherable_type": {"option_list": GATHER_TYPE_LIST, "pady": (30, 0),},
            "tool": {"option_list": TOOL_QUALITY_LIST,},
            "follower": {"option_list": FOLLOWER_LIST,},
            "weather": {"option_list": WEATHER_LIST,},
            "trait": {"option_list": TRAIT_LIST,},
            "season": {"option_list": SEASON_LIST},
            "time": {"option_list": TIME_LIST},
        }
        for key in self.dict_filter.keys():
            self.dict_filter[key]["menu"] = self.get_ctk_option_menu(
                self.dict_filter[key]["option_list"]
            )
            self.create_button_reverse(
                menu=self.dict_filter[key]["menu"],
                option=key,
                index=self.filter_iterable,
                pady=self.dict_filter[key]["pady"]
                if "pady" in self.dict_filter[key].keys()
                else None,
            )

        ### Display Grid
        ### Frame for the Filters
        self.display_frame = ctk.CTkFrame(self, width=900)
        self.display_frame.grid(
            row=0, column=2, padx=(20, 20), pady=(20, 20), sticky="nsew"
        )

        ### Search Grid
        self.search_frame = ctk.CTkEntry(
            self, width=900, height=50, border_width=2, corner_radius=10
        )
        self.search_frame.grid(
            row=1, column=2, padx=(20, 20), pady=(5, 20), sticky="ew"
        )
        self.prev_search_frame = self.search_frame.get()

    def get_display_items(self):
        """
        Get the items to display.
        """ 
        ### Get all Current Filters
        set_default = {OPTION_MENU[key] for key in OPTION_MENU.keys()}

        ### Manual garbage collection just incase
        for i, _ in enumerate(self.list_display_labels):
            self.list_display_labels[i].destroy()
        self.list_display_labels = []
        self.dict_display = {}

        if set_default == {}:
            return

        dict_curr_filters = {
            key: self.dict_filter[key]["menu"].get()
            for key in self.dict_filter.keys()
            if self.dict_filter[key]["menu"].get() not in set_default
        }

        ### Check if searchable empty and filters are set
        if len(dict_curr_filters) == 0 and self.search_frame.get() == "":
            return

        ### Query the list of items from filter and loop through list 
        ### and pick only the ones that are not in the filter
        for key in ITEM_DICT.keys():
            add_to_list = True
            for filt in dict_curr_filters.keys():
                if filt == "gatherable_type":
                    if (
                        dict_curr_filters["gatherable_type"]
                        != ITEM_DICT[key]["gatherable_type"]
                    ):
                        add_to_list = False
                elif filt not in ITEM_DICT[key]["quality"].keys():
                    add_to_list = False
                elif dict_curr_filters[filt] != ITEM_DICT[key]["quality"][filt]:

                    ### logic for seasons compares seasons that have extra suffixes (Spring vs Spring w2)
                    ### SEASONS
                    if (
                        filt == "season"
                        and len(dict_curr_filters[filt]) > 6
                        and dict_curr_filters[filt][:6]
                        == ITEM_DICT[key]["quality"][filt][:6]
                    ):
                        continue
                    ### TOOLS
                    if filt == "tool":
                        tool_list = [i[0] for i in TOOL_QUALITY_LIST]
                        if tool_list.index(
                            ITEM_DICT[key]["quality"][filt]
                        ) < tool_list.index(dict_curr_filters[filt]):
                            continue
                    ### TIME
                    if filt == "time" and type(ITEM_DICT[key]["quality"][filt]) == set:
                        if dict_curr_filters[filt] in ITEM_DICT[key]["quality"][filt]:
                            continue

                    ### Logic for Not Rain
                    if (
                        filt == "weather"
                        and ITEM_DICT[key]["quality"][filt] == "Not Rain"
                        and dict_curr_filters[filt] != "Rain"
                    ):
                        continue

                    add_to_list = False

            if add_to_list:
                self.dict_display[key] = deepcopy(ITEM_DICT[key])

        ### Check if there is a search query
        if self.search_frame.get() != "":
            search_val = self.search_frame.get()
            self.dict_display = dict(
                sorted(
                    self.dict_display.items(),
                    key=lambda x: fuzz.ratio(search_val.lower(), x[0].lower()),
                    reverse=True,
                )
            )
            self.dict_display = {
                k: deepcopy(v)
                for k, v in self.dict_display.items()
                if fuzz.ratio(search_val.lower(), k.lower()) > 50
            }

        ### Changes display
        self.change_display()

    def get_ctk_option_menu(self, values: list):
        """
        Get the ctk option menu. 
        """
        return ctk.CTkOptionMenu(
            self.filter_frame,
            dynamic_resizing=False,
            values=[i[0] for i in values],
            command=self.refresh_event,
        )

    def create_button_reverse(self, menu: ctk.CTkOptionMenu, option: str, index: int, pady: tuple=(5, 0)):
        """
        Create the button to reverse the filter.

        Args:
            menu (ctk.CTkOptionMenu): The option menu to reverse.
            option (str): The option to reverse.
            index (int): The index of the option menu.
            pady (tuple, optional): The padding. Defaults to (5, 0).
        
        Returns:
            None
        """
        ### Set default
        if pady is None:
            pady = (5, 0)

        ### Option Menu drop down
        menu.grid(row=index, column=0, padx=10, pady=pady)
        menu.set(OPTION_MENU[option])

        ### Create a label to display reverse icon next to dropdown
        reverse = ctk.CTkButton(
            master=self.filter_frame,
            text="",
            image=self.reverse_icon,
            command=lambda: self.on_option_menu_reverse(menu, option),
            width=20,
            height=20,
        )

        reverse.grid(row=index, column=1, padx=5, pady=pady)

        self.filter_iterable += 1

    def full_reverse_filters(self):
        """
        Reverse all filters and search bar.
        """
        ### Reset filters
        for key in self.dict_filter.keys():
            self.on_option_menu_reverse(
                menu=self.dict_filter[key]["menu"], option=key, refresh=False
            )
        ### Reset search bar
        self.search_frame.delete(first_index=0, last_index=len(self.search_frame.get()))

        ### Get display
        self.get_display_items()

    def on_option_menu_reverse(self, menu, option, refresh=True):
        """
        Events that runs after a reverse of the option menu.
        """
        menu.set(OPTION_MENU[option])
        if refresh:
            self.refresh_event(None)
            ### Get display
            self.get_display_items()

    def refresh_event(self, values):
        """
        Refresh the display.
        """
        ### Refresh display
        self.list_display = []

        ### Query the current values of filter
        var = self.search_frame.get()

        self.get_display_items()

    def change_display(self):
        """
        Change the display.
        """
        if len(self.dict_display) == 0:
            ### Manual garbage collection just incase
            for i, _ in enumerate(self.list_display_labels):
                self.list_display_labels[i].destroy()

            self.list_display_labels = []
            self.dict_display = {}

        brass = dwebp(f"images/items/brass.webp")
        brass_image = ctk.CTkImage(brass, size=(30, 30))
        brass_color = rgb_to_hex(average_rgb(brass))

        star = dwebp(f"images/star.webp")
        star_image = ctk.CTkImage(star, size=(20, 20))

        ### Loops through the itemss
        for i, key in enumerate(self.dict_display.keys()):
            if i >= 4:
                return

            ### Get image
            image = dwebp(f"images/items/{key}.webp")
            item_image = ctk.CTkImage(image, size=(30, 30))

            hex_avg_color = rgb_to_hex(average_rgb(image))
            name_label = ctk.CTkButton(
                self.display_frame,
                text=separate_pascal_case(key),
                fg_color=hex_avg_color,
                compound="right",
                image=item_image,
                text_color="black",
                border_color="black",
                hover=False,
                font=("Helvetica", 16, "bold"),
            )
            name_label.grid(row=i, column=1)

            placement_y = 0.05 + (i / 4)
            name_label.place(rely=placement_y, relx=0.45, anchor=tk.CENTER)

            self.list_display_labels.append(name_label)

            ### Check for price
            brass_label = ctk.CTkButton(
                self.display_frame,
                text=ITEM_DICT[key]["price"],
                fg_color=brass_color,
                compound="right",
                image=brass_image,
                text_color="black",
                border_color="black",
                hover=False,
                font=("Helvetica", 12, "bold"),
            )
            brass_label.place(rely=placement_y, relx=0.6, anchor=tk.CENTER)
            self.list_display_labels.append(brass_label)

            ### Check for location
            # Get number of locations
            locations = ITEM_DICT[key]["location"]
            INCREMENT = 0.15
            relx_start = 0.525 - INCREMENT * len(locations) / 2
            
            # Create location label
            params = {
                        "text": "Location",
                        "fg_color": "white",
                        "rely": placement_y + 0.05,
                        "relx": relx_start,
                    }
            self._create_button(**params)
            ### Display all the locations
            for j, loc in enumerate(locations):
                params = {
                        "text": loc,
                        "fg_color": "#90EE90",
                        "rely": placement_y + 0.05,
                        "relx": relx_start + ((j + 1) * INCREMENT),
                    }
                self._create_button(**params)

            ### Check filters for spawn
            INCREMENT = 0.15
            QUALITY_HEIGHT_INCREMENT = 0.1
            if "spawn" in ITEM_DICT[key]:
                # Create item quality label
                spawn = ITEM_DICT[key]["spawn"]
                if "season" not in spawn:
                    relx_start = 0.525 - INCREMENT * len(spawn) / 2
                else:
                    relx_start = (
                        0.525 - INCREMENT * (len(spawn) - 1 + len(spawn["season"])) / 2
                    )
                    
                params = {
                        "text": f"Spawn Info",
                        "fg_color": "#ff6666",
                        "rely":placement_y + 0.10,
                        "relx": relx_start,
                        "image": season_icon,
                    }
                self._create_button(**params)

                ### Loop through spawn reqs
                # To keep track of next label s
                curr_label = 1
                for _, spa in enumerate(spawn):
                    val = ITEM_DICT[key]["spawn"][spa]
                    if spa in OPTION_MENU.keys():
                        if type(val) != set:
                            val = set([val])
                        if spa == "season":
                            for season_i in val:
                                ### Get Image for seasons
                                season_file_name = season_i.lower()[:6]
                                image_url = f"images/season/{season_file_name}.png"

                                season_img = Image.open(image_url)
                                ### Create the season icons
                                season_icon = ctk.CTkImage(season_img, size=(20, 20))

                                if image_url not in self.color_cache:
                                    self.color_cache[image_url] = rgb_to_hex(
                                        average_rgb(season_img)
                                    )
                                season_color = self.color_cache[image_url]
                                
                                params = {
                                        "text": f"Season:\n{season_i}",
                                        "fg_color": season_color,
                                        "rely":placement_y + 0.10,
                                        "relx": relx_start + (INCREMENT * curr_label),
                                        "image": season_icon,
                                    }
                                self._create_button(**params)
                                curr_label += 1
                        elif spa == "time":
                            for iter_t in val:
                                params = {
                                        "text": f"Time:\n{iter_t}",
                                        "fg_color": "white",
                                        "rely":placement_y + 0.10,
                                        "relx": relx_start + (INCREMENT * curr_label),
                                        "image": season_icon,
                                    }
                                self._create_button(**params)
                                curr_label += 1
                        else:
                            for v in val:
                                params = {
                                        "text": f'{spa.capitalize()}:\n{val}',
                                        "fg_color": "white",
                                        "rely":placement_y + 0.10,
                                        "relx": relx_start + (INCREMENT * curr_label),
                                        "image": season_icon,
                                    }
                                self._create_button(**params)
                                curr_label += 1
                    elif spa == "area":
                        params = {
                                "text": f"Area:\n{val}",
                                "fg_color": "white",
                                "rely":placement_y + 0.10,
                                "relx": relx_start + (INCREMENT * curr_label),
                                "image": season_icon,
                            }
                        self._create_button(**params)
                        curr_label += 1
                ### Update the initial positions for quality if spawn information exists
                placement_y += 0.05
                QUALITY_HEIGHT_INCREMENT = 0.11
                
            ### Check filters for Item Quality
            # star_image
            quality = ITEM_DICT[key]["quality"]

            quantity = 0
            for q in quality:
                if type(q) == set:
                    quantity += len(q)
                else: 
                    quantity += 1

            relx_start = 0.525 - INCREMENT * quantity / 2

            # Create item quality label
            params = {
                "text": "Item Quality",
                "fg_color": "black",
                "text_color": "white",
                "rely": placement_y + 0.10,
                "relx": relx_start,
                "image": star_image,
            }
            self._create_button(**params)

            # To keep track of next label
            curr_label = 1
            for _, qual in enumerate(quality):
                val = ITEM_DICT[key]["quality"][qual]
                if qual in OPTION_MENU.keys():
                    if type(val) != set:
                        val = set([val])
                    if qual == "season":
                        ### Set as set if not set
                        for v in val:
                            season_file_name = v.lower()[:6]
                            image_url = f"images/season/{season_file_name}.png"

                            season_img = Image.open(image_url)
                            ### Create the season icons
                            season_icon = ctk.CTkImage(season_img, size=(20, 20))

                            if image_url not in self.color_cache:
                                self.color_cache[image_url] = rgb_to_hex(
                                    average_rgb(season_img)
                                )
                            season_color = self.color_cache[image_url]
                            params = {
                                "text": f"Season:\n{v}",
                                "fg_color": season_color,
                                "text_color": "white",
                                "rely": placement_y + QUALITY_HEIGHT_INCREMENT,
                                "relx": relx_start + (INCREMENT * curr_label),
                                "image": season_icon,
                            }
                            self._create_button(**params)
                            curr_label += 1
                    elif qual == "time":
                        for iter_t in val:
                            params = {
                                "text": f"Time:\n{iter_t}",
                                "fg_color": "White",
                                "rely": placement_y + QUALITY_HEIGHT_INCREMENT,
                                "relx": relx_start + (INCREMENT * curr_label),
                            }
                            self._create_button(**params)
                            curr_label += 1
                    elif qual == "trait":
                        for trait_i in val:
                            image_url = f"images/trait/{trait_i.capitalize()}.webp"
                            image = dwebp(image_url)

                            trait_image = ctk.CTkImage(image, size=(20, 20))
                            trait_color = rgb_to_hex(average_rgb(image))
                            
                            params = {
                                "text": f"Trait:\n{trait_i}",
                                "fg_color": trait_color,
                                "text_color": "white",
                                "rely": placement_y + QUALITY_HEIGHT_INCREMENT,
                                "relx": relx_start + (INCREMENT * curr_label),
                                "image": trait_image,
                            }
                            self._create_button(**params)
                            curr_label += 1
                    elif qual == "tool":
                        for v in val:
                            tool_dict = {
                                "Mining": "Pickaxe",
                                "Fishing": "Rod",
                                "Growing": "Sickle",
                                "Shooting": "Slingshot",
                                "Gathering": "Sickle",
                            }
                            tool = tool_dict[ITEM_DICT[key]['gatherable_type']]
                            params = {
                                "text": f'{tool}:\n{v}',
                                "fg_color": "Grey",
                                "rely": placement_y + QUALITY_HEIGHT_INCREMENT,
                                "relx": relx_start + (INCREMENT * curr_label),
                            }
                            self._create_button(**params)
                            curr_label += 1
                    else:
                        for v in val:
                            params = {
                                "text": f'{qual.capitalize()}:\n{v}',
                                "fg_color": "White",
                                "rely": placement_y + QUALITY_HEIGHT_INCREMENT,
                                "relx": relx_start + (INCREMENT * curr_label),
                            }
                            self._create_button(**params)
                            curr_label += 1
                elif qual == "misc":
                    if type(val) != set:
                        val = set([val])
                    for v in val:
                        params = {
                            "text": f"Misc:\n{v}",
                            "fg_color": "#E5E8E8",
                            "rely": placement_y + QUALITY_HEIGHT_INCREMENT,
                            "relx": relx_start + (INCREMENT * curr_label),
                        }
                        self._create_button(**params)
                        curr_label += 1
                elif qual == "ride":
                    params = {
                        "text": f"Ride:\n{val}",
                        "fg_color": "pink",
                        "rely": placement_y + QUALITY_HEIGHT_INCREMENT,
                        "relx": relx_start + (INCREMENT * curr_label),
                    }
                    self._create_button(**params)
                    curr_label += 1
                elif qual == "has":
                    params = {
                        "text": f"Has:\n{val}",
                        "fg_color": "red",
                        "rely": placement_y + QUALITY_HEIGHT_INCREMENT,
                        "relx": relx_start + (INCREMENT * curr_label),
                    }

                    self._create_button(**params)
                    curr_label += 1
                elif qual == "poo":
                    ### Get poo images
                    image_url = f"images/items/poo.webp"
                    poo_bucket_img = dwebp(image_url)
                    poo_image = ctk.CTkImage(poo_bucket_img, size=(20, 20))
                    
                    params = {
                        "text": f"Fertilizer:\n{val} Poo",
                        "fg_color": "brown",
                        "text_color": "white",
                        "rely": placement_y + QUALITY_HEIGHT_INCREMENT,
                        "relx": relx_start + (INCREMENT * curr_label),
                        "image": poo_image,
                    }

                    self._create_button(**params)
                    curr_label += 1
                    
    def _create_button(self, 
                       text: str,
                       fg_color: str,
                       rely: float,
                       relx: float,
                       text_color: str="black",
                       image: Image=None) -> None:
        """
        Creates a button with the given parameters

        Parameters
        ----------
        text : str
            The text to display on the button
        fg_color : str
            The foreground color of the button
        rely : float
            The y position of the button
        relx : float
            The x position of the button
        text_color : str, optional
            The color of the text, by default "black"
        image : Image, optional
            The image to display on the button, by default None

        Returns
        -------
        None
        """
        label = ctk.CTkButton(
            self.display_frame,
            text=text,
            fg_color=fg_color,
            compound="right",
            image=image,
            text_color=text_color,
            border_color="black",
            hover=False,
            font=("Helvetica", 12, "bold"),
        )
        label.place(
            rely=rely,
            relx=relx,
            anchor=tk.CENTER,
        )
            
        
        self.list_display_labels.append(label)
    
    
    def start(self):
        """
        Starts the mainloop of the application
        """
        while True:
            var = self.search_frame.get()
            if var == "":
                self.prev_search_frame = self.search_frame.get()
            elif self.prev_search_frame != var:
                self.prev_search_frame = self.search_frame.get()
                self.get_display_items()

            self.update_idletasks()
            self.update()

if __name__ == "__main__":
    app = App()
    app.start()