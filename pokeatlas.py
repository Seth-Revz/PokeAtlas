import hashlib
import pathlib
import shutil
import sys
import zipfile
from collections import Counter
from textwrap import dedent

from PIL import Image

class Atlas():
    def __init__(self, atlas_path: pathlib.Path, img_name: str, img_size: str, img_format: str, img_filter: str, repeat: str):
        self.atlas_path = atlas_path
        self.img_name = img_name
        self.img_size = img_size
        self.img_format = img_format
        self.img_filter = img_filter
        self.repeat = repeat
        self.sprites = {}
        self.sprite_hashes = {}
    
    def add_sprite(self, name, attributes):
        self.sprites[name] = attributes
    
    def add_sprite_hash(self, name, hash):
        self.sprite_hashes[name] = hash

    def get_sprites(self) -> dict:
        return self.sprites

def get_atlas(path: pathlib.Path) -> Atlas:
    t = path.read_text().strip().split('\n')

    atlas = Atlas(path.absolute(), *[ t.strip().split(': ')[1] if ': ' in t else t for t in t[:5] ])

    for line in t[5:]:
        line = line.strip()

        if ':' not in line:
            sprite_name = line
            attributes = {'name': sprite_name}
        else:
            name, value = line.strip().split(': ')
            attributes[name] = value

            if name == 'index':
                if int(value) >= 0:
                    sprite_name = f'{sprite_name}_{value}'

                atlas.add_sprite(sprite_name, attributes)

    return atlas

def get_image_hash(image_path: pathlib.Path) -> str:
    return hashlib.md5(image_path.read_bytes()).hexdigest()

def decomp(atlas: Atlas):
    atlas_dir = atlas.atlas_path.parent
    atlas_img = Image.open(atlas_dir / atlas.img_name)
    sprites_dir = atlas_dir / 'sprites'
    sprites_dir.mkdir(exist_ok=True)
    
    for sprite_name, attributes in atlas.get_sprites().items():

        left = int(attributes['xy'].split(', ')[0])
        top = int(attributes['xy'].split(', ')[1])
        right = left + int(attributes['size'].split(', ')[0])
        bottom = top + int(attributes['size'].split(', ')[1])

        sprite = atlas_img.crop((left, top, right, bottom))

        sprite.save(sprites_dir / f'{sprite_name}.png')
        atlas.add_sprite_hash(sprite_name, get_image_hash(sprites_dir / f'{sprite_name}.png'))

def find_duplicates(atlas: Atlas) -> list:
    sprites = atlas.get_sprites()

    attributes = sprites.values()
    coord_counts = Counter(d['xy'] for d in attributes)
    duplicate_coords = {coord for coord,
                        count in coord_counts.items() if count > 1}

    result = [sprite_name for sprite_name,
              d in sprites.items() if d['xy'] in duplicate_coords]

    return result

def check_duplicates(atlas: Atlas):
    atlas_dir = atlas.atlas_path.parent
    sprites_dir = atlas_dir / 'sprites'
    duplicates = find_duplicates(atlas)

    modified_dupe_sprites = []

    for sprite_name, attributes in atlas.get_sprites().items():
        if atlas.sprite_hashes[sprite_name] != get_image_hash(sprites_dir / f'{sprite_name}.png'):
            if sprite_name in duplicates:
                modified_dupe_sprites.append((sprite_name, attributes))

    for sprite_name, attributes in modified_dupe_sprites:

        atlas.get_sprites().pop(sprite_name)
        atlas.add_sprite(sprite_name, attributes)

        removed_hash = atlas.sprite_hashes.pop(sprite_name)
        atlas.add_sprite_hash(sprite_name, removed_hash)
        
def rebuild(atlas: Atlas):
    canvas = Image.new('RGBA', tuple(map(int, atlas.img_size.split(', '))), (255,255,255,0))

    for sprite_name, attributes in atlas.get_sprites().items():
        sprite = Image.open(atlas.atlas_path.parent / 'sprites' / f'{sprite_name}.png')
        canvas.paste(sprite, tuple(map(int, attributes['xy'].split(', '))))
    
    output_dir = atlas.atlas_path.parent / 'output'
    output_dir.mkdir(exist_ok=True)

    canvas.save(output_dir / atlas.img_name)

def export_mod_full(atlas: Atlas, icon_path: pathlib.Path):
    rebuild(atlas)

    atlas_dir = atlas.atlas_path.parent
    sprites_dir = atlas_dir / 'sprites'
    output_dir = atlas.atlas_path.parent / 'output'
    output_dir.mkdir(exist_ok=True)
    mod_dir = output_dir / 'mod_full'
    if mod_dir.exists() and mod_dir.is_dir():
        shutil.rmtree(mod_dir)

    atlas_mod_dir = pathlib.Path(mod_dir / 'data' / 'sprites' / 'atlas')
    atlas_mod_dir.mkdir(exist_ok=True, parents=True)
    atlas_text_file = atlas_mod_dir / 'main.atlas'

    atlas_text_file.write_text(
        dedent(f"""
            {atlas.img_name}
            size: {atlas.img_size}
            format: {atlas.img_format}
            filter: {atlas.img_filter}
            repeat: {atlas.repeat}
        """)
    )

    canvas = Image.new('RGBA', tuple(map(int, atlas.img_size.split(', '))), (255,255,255,0))

    with atlas_text_file.open(mode='a') as file:
        for sprite, attributes in atlas.get_sprites().items():
            file.write(f"{attributes['name']}\n")
            file.write(f"  rotate: {attributes['rotate']}\n")
            file.write(f"  xy: {attributes['xy']}\n")
            file.write(f"  size: {attributes['size']}\n")
            file.write(f"  orig: {attributes['orig']}\n")
            file.write(f"  offset: {attributes['offset']}\n")
            file.write(f"  index: {attributes['index']}\n")

            sprite_image = Image.open(sprites_dir / f'{sprite}.png')
            canvas.paste(sprite_image, tuple(map(int, attributes['xy'].split(', '))))

    canvas.save(atlas_mod_dir / atlas.img_name)

    pathlib.Path(mod_dir / 'info.xml').write_text(
        dedent("""
            <?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <resource author="Revz" description="Created with PokeAtlas" name="Revz Atlas" version="1" weblink="">
                <overlays>
                    <overlay path="data/sprites/atlas/"/>
                </overlays>
            </resource>
        """.strip('\n'))
    )

    shutil.copy(icon_path, str(pathlib.Path(mod_dir / 'icon.png')))
    
    with zipfile.ZipFile(str(output_dir / 'FullAtlas.mod'), 'w') as zipf:
        for file_path in mod_dir.rglob('*'):
            zipf.write(file_path, arcname=file_path.relative_to(mod_dir))


def export_mod_modified(atlas: Atlas, icon_path: pathlib.Path):
    atlas_dir = atlas.atlas_path.parent
    sprites_dir = atlas_dir / 'sprites'
    output_dir = atlas.atlas_path.parent / 'output'
    output_dir.mkdir(exist_ok=True)
    mod_dir = output_dir / 'mod_partial'
    
    if mod_dir.exists() and mod_dir.is_dir():
        shutil.rmtree(mod_dir)

    all_sprites = atlas.get_sprites()
    edited_sprites = []

    atlas_mod_dir = pathlib.Path(mod_dir / 'data' / 'sprites' / 'atlas')
    atlas_mod_dir.mkdir(exist_ok=True, parents=True)
    atlas_text_file = atlas_mod_dir / 'main.atlas'

    height = 0
    width = 0
    
    for sprite_name in all_sprites:
        if atlas.sprite_hashes[sprite_name] != get_image_hash(sprites_dir / f'{sprite_name}.png'):
            edited_sprites.append(sprite_name)

    for edited_sprite in edited_sprites:
        attributes = all_sprites[edited_sprite]
        width = max(width, int(attributes['size'].split(', ')[0]))
        height += int(attributes['size'].split(', ')[1])

    atlas_text_file.write_text(
        dedent(f"""
            {atlas.img_name}
            size: {width}, {height}
            format: {atlas.img_format}
            filter: {atlas.img_filter}
            repeat: {atlas.repeat}
        """)
    )

    canvas = Image.new('RGBA', (width, height), (255,255,255,0))

    current_height = 0
    with atlas_text_file.open(mode='a') as file:
        for edited_sprite in edited_sprites:
            attributes = all_sprites[edited_sprite]

            file.write(f"{attributes['name']}\n")
            file.write(f"  rotate: {attributes['rotate']}\n")
            file.write(f"  xy: {0}, {current_height}\n")
            file.write(f"  size: {attributes['size']}\n")
            file.write(f"  orig: {attributes['orig']}\n")
            file.write(f"  offset: {attributes['offset']}\n")
            file.write(f"  index: {attributes['index']}\n")

            sprite_image = Image.open(sprites_dir / f'{edited_sprite}.png')
            canvas.paste(sprite_image, (0, current_height))

            current_height += int(attributes['size'].split(', ')[1])

    canvas.save(atlas_mod_dir / atlas.img_name)

    pathlib.Path(mod_dir / 'info.xml').write_text(
        dedent("""
            <?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <resource author="Revz" description="Created with PokeAtlas" name="Revz Atlas" version="1" weblink="">
                <overlays>
                    <overlay path="data/sprites/atlas/"/>
                </overlays>
            </resource>
        """.strip('\n'))
    )

    shutil.copy(icon_path, str(pathlib.Path(mod_dir / 'icon.png')))
    
    with zipfile.ZipFile(str(output_dir / 'PartialAtlas.mod'), 'w') as zipf:
        for file_path in mod_dir.rglob('*'):
            zipf.write(file_path, arcname=file_path.relative_to(mod_dir))

def resource_path(relative: pathlib.Path):
    try:
        base_path = pathlib.Path(sys._MEIPASS)
    except Exception:
        base_path = pathlib.Path('.')

    return base_path / relative

if __name__ == '__main__':
    from ui.mainwindow import MainWindow
    from PySide6.QtWidgets import QApplication
    import qdarktheme

    try:
        from ctypes import windll
        windll.shell32.SetCurrentProcessExplicitAppUserModelID('com.revz.pokeatlas')
    except ImportError:
        pass

    icon_path = resource_path(pathlib.Path('ui/icon.png'))

    app = QApplication()
    qdarktheme.setup_theme('dark')
    mainwindow = MainWindow(icon_path=icon_path)
    mainwindow.show()
    app.exec()