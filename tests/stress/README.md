# Stress-test documents

Small LaTeX documents that put the converter under pressure: many kinds of mathematics (`s1_math`),
a two-column paper with a wide figure, wide tables and an algorithm (`s2_twocol`), figures and tables
in awkward forms such as wrapped, rotated and page-spanning tables (`s3_figtab`) and Times-font maths
with margin notes and footnotes (`s4_times`).

The PDFs are committed so the tests need no TeX installation. To rebuild them, run `pdflatex` twice
on each `.tex` file. `s2_twocol` and `s3_figtab` include charts (`lines.pdf`, `bars.pdf`,
`scatter.pdf`, `heat.pdf`) and a picture (`photo.png`) made with matplotlib and numpy.
