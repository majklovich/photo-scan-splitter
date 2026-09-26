# Rozdělení naskenované stránky na fotografie

Malá desktopová aplikace v Pythonu, která rozdělí sken stránky A4 se čtyřmi fotografiemi na čtyři samostatné soubory PNG.

## Požadavky

- Python 3.9 nebo novější
- Tkinter (bývá součástí instalace Pythonu)

## Instalace a spuštění

V terminálu v této složce spusťte:

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

## Použití

1. Zvolte **Vybrat sken...** a otevřete obrázek stránky.
2. Posuňte svislý a vodorovný řez tak, aby procházely mezerami mezi fotografiemi.
3. Zvolte **Rozdělit a uložit 4 fotografie...** a vyberte cílovou složku.

Výsledkem budou soubory `fotografie_1.png` až `fotografie_4.png`, seřazené zleva doprava a shora dolů. Podporované vstupní formáty jsou JPG, PNG, TIFF, BMP a WebP. Původní sken se nemění.