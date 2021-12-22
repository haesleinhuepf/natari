import napari
from napari_tools_menu import register_action


@register_action(menu="Games > Sliding Puzzle")
def sliding_puzzle(viewer: napari.Viewer):
    game = SlidingPuzzleGame.instance(viewer)
    game.start()


class SlidingPuzzleGame():
    """
    In the sliding puzzle game, the current image lay is split in tiles and the user can move tiles around by
    exchanging neighboring tiles. At the start, tiles are exchanged randomly and a given starting tile is replaced
    by a black square. The use can then use the WASD keys on the keyboard to move the replace the black tile with
    neighbor tiles.
    """
    def __init__(self, viewer: napari.Viewer):
        """
        This function is called only once because we don't want to add multiple key handlers and
        background threads to the viewer.
        """
        from napari._qt.qthreading import thread_worker
        import time
        self.game_layer = None
        self.pos_x = 0
        self.pos_y = 0
        self.height = 0
        self.width = 0
        self.viewer = viewer
        self.image = None

        def update_layers(data):
            """
            This function is called when a new game state has been computed in the background thread.
            It is responsible for updating the viewer in the main thread
            """
            if self.game_layer is not None:
                self.game_layer.data = data

        @thread_worker
        def loop_run():
            """
            This is an endless loop executing actions if the user hit a key.
            """
            while True:  # endless loop
                data = self.game_loop()
                yield data
                time.sleep(0.05)

        # Start the loop
        worker = loop_run()
        worker.yielded.connect(update_layers)
        worker.start()

        # Key bindings for the game
        @viewer.bind_key('w', overwrite=True)
        def player_up_event(viewer):
            if self.pos_y > 0:
                self.game_chain.append('w')

        @viewer.bind_key('a', overwrite=True)
        def player_left_event(viewer):
            if self.pos_x > 0:
                self.game_chain.append('a')

        @viewer.bind_key('s', overwrite=True)
        def player_down_event(viewer):
            if self.pos_y < (self.height / self.patch_size) - 1:
                self.game_chain.append('s')

        @viewer.bind_key('d', overwrite=True)
        def player_right_event(viewer):
            if self.pos_x < (self.width / self.patch_size) - 1:
                self.game_chain.append('d')

        @viewer.bind_key('r', overwrite=True)
        def player_random_next_step(viewer):
            """
            Make a random move.
            """
            self.game_chain = self.game_chain + make_random_game(self.pos_x,self.pos_y,self.image,self.patch_size,1)

        @viewer.bind_key('f', overwrite=True)
        def player_find_home(viewer):
            """
            Revert the game state and go back to the start.

            That's an Easter egg.

            Let's see who reads the code or hits the F key by chance.
            """
            copy = self.game_chain.copy()
            copy.reverse()
            list_replace(copy, 'w', 't')
            list_replace(copy, 's', 'w')
            list_replace(copy, 't', 's')
            list_replace(copy, 'a', 't')
            list_replace(copy, 'd', 'a')
            list_replace(copy, 't', 'd')
            self.game_chain = self.game_chain + copy

    @classmethod
    def instance(cls, viewer):
        """
        This is a singleton implementation.
        """
        if not hasattr(cls, "_instance"):
            cls._instance = SlidingPuzzleGame(viewer)
        return cls._instance

    def start(self):
        """
        Start the game on the current layer. If no layer is open, load Pixel the cat.
        """
        from skimage.io import imread, imshow
        from pathlib import Path

        # game config
        self.patch_size = 100

        self.pos_x = 0
        self.pos_y = 0

        self.game_state = 0
        self.game_chain = []

        # if no layer open, load a picture of Pixel
        if len(self.viewer.layers) == 0:
            data_path = Path(__file__).parent / "data"
            dataset = imread(data_path / '17157718_1475080609170139_6436185275063838511_o.jpg')
            self.viewer.add_image(dataset[100:1000,400:1600].copy())

        # initialize image
        self.image = list(self.viewer.layers.selection)[0].data
        self.image = crop_image(self.image, self.patch_size).copy()
        draw_grid(self.image, self.patch_size)
        self.width = self.image.shape[1]
        self.height = self.image.shape[0]

        # initialize layer and tiles
        self.game_layer = self.viewer.add_image(self.image)
        start_x = int(self.width / 2 / self.patch_size)
        start_y = int(self.height / 2 / self.patch_size)
        set_tile_to_zero(self.image, start_x, start_y, self.patch_size)

        # initialize the game with a random walk
        length = 50
        self.game_chain = make_random_game(start_x, start_y, self.image, self.patch_size, length)
        self.game_state = 0

        self.pos_x = start_x
        self.pos_y = start_y


    def game_loop(self):
        """
        This function runs in an endless loop in the background.
        In case the use hit a key, it will update the game state.
        """
        if self.game_state < len(self.game_chain):
            if self.game_state < 0:
                direction = self.game_chain[-1]
            else:
                direction = self.game_chain[self.game_state]

            former_pos_x = self.pos_x
            former_pos_y = self.pos_y

            self.pos_x, self.pos_y = new_pos(self.pos_x, self.pos_y, direction)

            if not exchange_tiles(self.image, former_pos_x, former_pos_y, self.pos_x, self.pos_y, self.patch_size):
                self.pos_x = former_pos_x
                self.pos_y = former_pos_y

            if self.game_state == -1:
                self.game_chain = self.game_chain[:-1]
                self.game_state = len(self.game_chain)
            else:
                self.game_state += 1

        return self.image


def make_random_game(start_x, start_y, image, patch_size, length):
    """
    Sets up a random walk for the game start. The path will not contain subsequent up/down and left/right steps.
    """
    import numpy as np
    directions = ['w', 'a', 's', 'd']
    width = image.shape[1] / patch_size
    height = image.shape[0] / patch_size

    path = []
    pos_x = start_x
    pos_y = start_y

    while len(path) < length:
        direction = directions[np.random.randint(0, 4)]

        former_pos_x = pos_x
        former_pos_y = pos_y

        pos_x, pos_y = new_pos(pos_x, pos_y, direction)
        if pos_x >= width-1 or pos_x < 0 or pos_y >= height-1 or pos_y < 0:
            pos_x = former_pos_x
            pos_y = former_pos_y
        else:
            path.append(direction)

        if len(path) > 2:
            if path[-3:-1] in ['ws', 'sw', 'ad', 'da']:
                path = path[:-2]

    return path


def list_replace(lst, a, b):
    for i in range(len(lst)):
        if lst[i] == a:
            lst[i] = b


def crop_image(image, patch_size):
    new_width = int(image.shape[1] / patch_size) * patch_size
    new_height = int(image.shape[0] / patch_size) * patch_size

    return image[:new_height, :new_width, ...]


def set_tile_to_zero(image, x, y, patch_size):
    image[y * patch_size:(y + 1) * patch_size, x * patch_size:(x + 1) * patch_size] = 0


def exchange_tiles(image, x1, y1, x2, y2, patch_size):
    try:
        tile1 = image[y1 * patch_size:(y1 + 1) * patch_size, x2 * patch_size:(x2 + 1) * patch_size].copy()
        tile2 = image[y2 * patch_size:(y2 + 1) * patch_size, x1 * patch_size:(x1 + 1) * patch_size].copy()

        image[y1 * patch_size:(y1 + 1) * patch_size, x2 * patch_size:(x2 + 1) * patch_size] = tile2
        image[y2 * patch_size:(y2 + 1) * patch_size, x1 * patch_size:(x1 + 1) * patch_size] = tile1
        return True
    except:
        return False


def new_pos(pos_x, pos_y, direction):
    if direction == 'w':
        pos_y -= 1
    elif direction == 'a':
        pos_x -= 1
    elif direction == 's':
        pos_y += 1
    elif direction == 'd':
        pos_x += 1

    return pos_x, pos_y


def draw_grid(image, patch_size):
    width = image.shape[1]
    height = image.shape[0]
    
    for x in range(int(width / patch_size)):
        image[:, x * patch_size-1:x * patch_size+1] = 0
    for y in range(int(height / patch_size)):
        image[y * patch_size-1:y * patch_size+1] = 0
