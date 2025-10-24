PokeAtlas
==========  

<img alt='pokeatlas_img' width=600 src='https://github.com/Seth-Revz/PokeAtlas/blob/main/.github/pokeatlas.png'>  

PokeAtlas is a python application designed to decompile the main.atlas and main.png sprite sheet used in [PokeMMO themes](https://forums.pokemmo.com/index.php?/forum/33-client-customization/) into separate sprites, making it easy to replace them.  
Once edited, the tool recompiles the main.png image (where all the sprites are) using the updated sprites.  

PokeAtlas was created to save time updating the atlas file after each game update. 

## Requirements  

- [Python](https://www.python.org/downloads/)  3.12.X max
- [PySide6](https://pypi.org/project/PySide6/)  
- [PyQtDarkTheme](https://pypi.org/project/pyqtdarktheme/)  
- [Pillow](https://pypi.org/project/pillow/)  

## Getting Started  

Clone the source code with `git` or download it as a .zip file.  

```bash
git clone https://github.com/Seth-Revz/PokeAtlas.git
cd PokeAtlas
pip install -r requirements.txt --ignore-requires-python
python pokeatlas.py
```

Or download the latest [release](https://github.com/Seth-Revz/PokeAtlas/releases/latest) (Windows Only)

Web version is also available now. [pokeatlas-web](https://github.com/Seth-Revz/pokeatlas-web)
