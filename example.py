import pyslides

firstslide = pyslides.newSlide()
firstslide.background("filehere")

sometext = firstslide.addText("Hello")
sometext.font("Rubik")
sometext.fontSize(24)
sometext.width(80) #based on percent, fills up 80% of the screen
sometext.scale(1.2) #20% larger than normal, makes it fill up 96% of the screen

sometext.anchor(1) #position is anchored to the top left of the text
# 1 2 3
# 4 5 6
# 7 8 9
sometext.position(0, 0) #based on percent
print(pyslides.width()) #errors if you run it before you use the "start slides" function, but would print out the width of the screen


