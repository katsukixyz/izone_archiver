import os
import shutil

for folder in os.listdir("D:/izone/"):
    for item in os.listdir("D:/izone/"+folder):
        if item == "link.txt":
            os.remove("D:/izone/" + folder + '/' + item)
        # if os.path.isdir("D:/izone/" + folder + '/' + item):
            # shutil.rmtree("D:/izone/" + folder + '/' + item)