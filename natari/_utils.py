def draw_box(image, x, y, z, w, h, d, value=1):
    image[int(y):int(y+h), int(x):int(x+w)].fill(value)
