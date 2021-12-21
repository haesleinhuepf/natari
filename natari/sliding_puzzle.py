import napari
from napari_tools_menu import register_action

# game config
patch_size = 100

current_pos_x = 0
current_pos_y = 0

game_state = 0
game_chain = []


@register_action(menu="Games > Sliding Puzzle")
def sliding_puzzle(viewer : napari.Viewer):
    # global variables are not good.
    # Only in cheap game programming it's ok.
    global game_chain

    from napari._qt.qthreading import thread_worker
    from skimage.io import imread, imshow
    from pathlib import Path
    import time

    if len(viewer.layers) == 0:
        data_path = Path(__file__).parent / "data"
        dataset = imread(data_path / '17157718_1475080609170139_6436185275063838511_o.jpg')
        viewer.add_image(dataset[100:1000,400:1600])

    # start game
    image = list(viewer.layers.selection)[0].data
    image = crop_image(image, patch_size).copy()
    width = image.shape[1]
    height = image.shape[0]

    game_layer = viewer.add_image(image)

    start_x = int(width / 2 / patch_size)
    start_y = int(height / 2 / patch_size)
    set_tile_to_zero(image, start_x, start_y, patch_size)

    length = 50
    game_chain = make_random_game(start_x, start_y, image, patch_size, length)

    def update_layers(data):
        game_layer.data = data

    @thread_worker
    def loop_run(data, pos_x, pos_y):
        global current_pos_y
        global current_pos_x
        while True:  # endless loop
            data, pos_x, pos_y = game_loop(data, pos_x, pos_y)
            current_pos_x = pos_x
            current_pos_y = pos_y
            yield data
            time.sleep(0.05)

    # Start the loop
    worker = loop_run(image, start_x, start_y)
    worker.yielded.connect(update_layers)
    worker.start()

    # Key bindings for the game
    @viewer.bind_key('w')
    def player_up_event(viewer):
        global current_pos_y
        if current_pos_y > 0:
            game_chain.append('w')

    @viewer.bind_key('a')
    def player_left_event(viewer):
        global current_pos_x
        if current_pos_x > 0:
            game_chain.append('a')

    @viewer.bind_key('s')
    def player_down_event(viewer):
        global current_pos_y
        if current_pos_y < height / patch_size:
            game_chain.append('s')

    @viewer.bind_key('d')
    def player_right_event(viewer):
        global current_pos_x
        if current_pos_x < width / patch_size:
            game_chain.append('d')

    @viewer.bind_key('r')
    def player_random_next_step(viewer):
        global game_chain
        game_chain = game_chain + make_random_game(current_pos_x,current_pos_y,image,patch_size,1)

    @viewer.bind_key('f')
    def player_find_home(viewer):
        global game_chain
        copy = game_chain
        copy.reverse()
        list_replace(copy, 'w', 't')
        list_replace(copy, 's', 'w')
        list_replace(copy, 't', 's')
        list_replace(copy, 'a', 't')
        list_replace(copy, 'd', 'a')
        list_replace(copy, 't', 'd')
        game_chain = game_chain + copy

def list_replace(lst, a, b):
    for i in range(len(lst)):
        if lst[i] == a:
            lst[i] = b

def game_loop(image, pos_x, pos_y):
    global game_state, game_chain

    if(game_state != len(game_chain)):
        if game_state < 0:
            direction = game_chain[-1]
        else:
            direction = game_chain[game_state]

        print(direction)

        former_pos_x = pos_x
        former_pos_y = pos_y

        pos_x, pos_y = new_pos(pos_x, pos_y, direction)

        print(former_pos_x, former_pos_y, '->', pos_x, pos_y)

        exchange_tiles(image, former_pos_x, former_pos_y, pos_x, pos_y)

        if game_state == -1:
            game_chain = game_chain[:-1]
            game_state = len(game_chain)
        else:
            game_state += 1

        print(game_state)

    return image, pos_x, pos_y

def crop_image(image, patch_size):
    new_width = int(image.shape[1] / patch_size) * patch_size
    new_height = int(image.shape[0] / patch_size) * patch_size

    return image[:new_height, :new_width, ...]


def set_tile_to_zero(image, x, y, patch_size):
    image[y * patch_size:(y + 1) * patch_size, x * patch_size:(x + 1) * patch_size] = 0


def exchange_tiles(image, x1, y1, x2, y2):
    tile1 = image[y1 * patch_size:(y1 + 1) * patch_size, x2 * patch_size:(x2 + 1) * patch_size].copy()
    tile2 = image[y2 * patch_size:(y2 + 1) * patch_size, x1 * patch_size:(x1 + 1) * patch_size].copy()

    image[y1 * patch_size:(y1 + 1) * patch_size, x2 * patch_size:(x2 + 1) * patch_size] = tile2
    image[y2 * patch_size:(y2 + 1) * patch_size, x1 * patch_size:(x1 + 1) * patch_size] = tile1


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


def make_random_game(start_x, start_y, image, patch_size, length):
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
        if pos_x >= width or pos_x < 0 or pos_y >= height or pos_y < 0:
            pos_x = former_pos_x
            pos_y = former_pos_y
        else:
            path.append(direction)

        if len(path) > 2:
            if path[-3:-1] in ['ws', 'sw', 'ad', 'da']:
                print("hit")
                path = path[:-2]

    return path


