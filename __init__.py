import pygame
import math
import time
import sys
import os

pygame.init()
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Slides!")
clock = pygame.time.Clock()

class SlideObject:
    def __init__(self, obj_type):
        self.type = obj_type
        self.props = {}
        self.visible = False

class Slide:
    def __init__(self, name):
        self.name = name
        self.methods = {}

    def add_method(self, name, args, body):
        self.methods[name] = (args, body)

class Interpreter:
    slides = {}
    global_vars = {}
    objects = {}
    slide_order = []
    current_slide_index = 0
    start_time = 0
    transitioning = False
    out_start_time = None
    running = True
    background = None
    slide_finished = False

    @staticmethod
    def parse_block(lines, i):
        block = []
        depth = 1
        i += 1
        while i < len(lines):
            line = lines[i].strip()
            if line == '{':
                depth += 1
            elif line == '}':
                depth -= 1
                if depth == 0:
                    return block, i
            else:
                block.append(line)
            i += 1
        raise Exception("Unmatched braces")

    @staticmethod
    def parse(lines):
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("slide"):
                name = line.split()[1]
                if "{" in line:
                    i += 1
                elif lines[i + 1].strip() == "{":
                    i += 2
                else:
                    raise Exception("Expected '{' after slide")
                slide = Slide(name)
                while i < len(lines) and lines[i].strip() != '}':
                    line = lines[i].strip()
                    if line.startswith("def"):
                        header = line[4:].split("(", 1)
                        method_name = header[0].strip()
                        args = header[1].split(")")[0].split(",") if "(" in line else []
                        args = [arg.strip() for arg in args if arg.strip()]
                        if "{" in line:
                            block, i = Interpreter.parse_block(lines, i)
                        else:
                            block, i = Interpreter.parse_block(lines, i + 1)
                        slide.add_method(method_name, args, block)
                    i += 1
                Interpreter.slides[name] = slide
            elif line.startswith("def"):
                func_name = line.split()[1].split("(")[0]
                if "{" in line:
                    block, i = Interpreter.parse_block(lines, i)
                else:
                    block, i = Interpreter.parse_block(lines, i + 1)
                Interpreter.global_vars[func_name] = ("function", [], block)
                i += 1
            else:
                i += 1

    @staticmethod
    def run():
        if "main" in Interpreter.global_vars:
            _, _, block = Interpreter.global_vars["main"]
            Interpreter.run_block(block, {})
        else:
            raise Exception("No main function found")

    @staticmethod
    def evaluate(expr, local_vars):
        try:
            expr = expr.replace("sin", "math.sin")
            expr = expr.replace("true", "True").replace("false", "False")
            expr = expr.replace("width", str(screen_width))
            expr = expr.replace("height", str(screen_height))
            return eval(expr, {"math": math}, {**Interpreter.global_vars, **local_vars})
        except Exception:
            return expr.strip('"').strip("'")

    @staticmethod
    def run_block(block, local_vars):
        for line in block:
            line = line.split("//")[0].strip().rstrip(";")
            if not line:
                continue
            if line.startswith("debug "):
                val = line[6:].strip()
                print("[DEBUG]", Interpreter.evaluate(val, local_vars))
            elif line.startswith("show "):
                obj_name = line[5:].strip()
                if obj_name in Interpreter.objects:
                    Interpreter.objects[obj_name].visible = True
            elif line.startswith("setslides "):
                names = [n.strip() for n in line[len("setslides "):].split(",")]
                Interpreter.slide_order = names
            elif line == "start":
                Interpreter.start_slideshow()
            elif line == "nextslide":
                Interpreter.slide_finished = True
            elif line.startswith("if "):
                condition, rest = line[3:].split("{", 1)
                condition = Interpreter.evaluate(condition.strip(), local_vars)
                block_code = rest.rstrip("}").strip()
                if condition:
                    Interpreter.run_block([block_code], local_vars)
            elif line.startswith("else if "):
                condition, rest = line[8:].split("{", 1)
                condition = Interpreter.evaluate(condition.strip(), local_vars)
                block_code = rest.rstrip("}").strip()
                if condition:
                    Interpreter.run_block([block_code], local_vars)
            elif line.startswith("else {"):
                block_code = line[5:].rstrip("}").strip()
                Interpreter.run_block([block_code], local_vars)
            elif "=" in line and "." not in line.split("=")[0]:
                var, val = line.split("=", 1)
                val = Interpreter.evaluate(val.strip(), local_vars)
                Interpreter.global_vars[var.strip()] = val
                if var.strip() == "background":
                    try:
                        path = val if isinstance(val, str) else str(val)
                        if os.path.exists(path):
                            image = pygame.image.load(path).convert()
                            Interpreter.background = pygame.transform.scale(image, (screen_width, screen_height))
                        else:
                            Interpreter.background = None
                    except:
                        Interpreter.background = None
            elif "." in line and "=" in line:
                obj_name, prop_expr = line.split(".", 1)
                prop, val = prop_expr.split("=", 1)
                val = Interpreter.evaluate(val.strip(), local_vars)
                Interpreter.objects[obj_name.strip()].props[prop.strip()] = val
            elif line.startswith("text "):
                _, name = line.split()
                Interpreter.objects[name] = SlideObject("text")
            elif line.startswith("image "):
                parts = line.split()
                name = parts[1]
                path = parts[2].strip('"') if len(parts) > 2 else ""
                obj = SlideObject("image")
                obj.props["path"] = path
                try:
                    obj.props["surf"] = pygame.image.load(path).convert_alpha()
                except:
                    obj.props["surf"] = None
                Interpreter.objects[name] = obj
            elif line.endswith(")"):
                if "(" in line:
                    name, arg_expr = line.split("(", 1)
                    args = [Interpreter.evaluate(x.strip(), local_vars) for x in arg_expr.rstrip(")").split(",") if x.strip()]
                    Interpreter.call_function(name.strip(), args)

    @staticmethod
    def call_function(name, args):
        if name in Interpreter.global_vars:
            _, arg_names, block = Interpreter.global_vars[name]
            local_vars = dict(zip(arg_names, args))
            Interpreter.run_block(block, local_vars)
        elif name in Interpreter.slides:
            slide = Interpreter.slides[name]
            if "init" in slide.methods:
                Interpreter.objects.clear()
                Interpreter.background = None
                Interpreter.run_block(slide.methods["init"][1], {})
        else:
            print("[WARN] Unknown function:", name)

    @staticmethod
    def start_slideshow():
        while Interpreter.current_slide_index < len(Interpreter.slide_order) and Interpreter.running:
            slide_name = Interpreter.slide_order[Interpreter.current_slide_index]
            slide = Interpreter.slides[slide_name]
            Interpreter.objects.clear()
            Interpreter.background = None
            Interpreter.slide_finished = False
            if "init" in slide.methods:
                Interpreter.run_block(slide.methods["init"][1], {})
            Interpreter.start_time = time.time()
            Interpreter.transitioning = False

            while not Interpreter.transitioning and Interpreter.running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        Interpreter.running = False
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                        Interpreter.transitioning = True
                        Interpreter.out_start_time = time.time()
                elapsed = (time.time() - Interpreter.start_time) * 1000
                screen.fill((0, 0, 0))
                if Interpreter.background:
                    screen.blit(Interpreter.background, (0, 0))
                if "loop" in slide.methods:
                    Interpreter.run_block(slide.methods["loop"][1], {"time": elapsed})
                Interpreter.draw_objects()
                pygame.display.flip()
                clock.tick(60)

            while not Interpreter.slide_finished and Interpreter.running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        Interpreter.running = False
                now = time.time()
                elapsed = (now - Interpreter.start_time) * 1000
                out_elapsed = (now - Interpreter.out_start_time) * 1000
                screen.fill((0, 0, 0))
                if Interpreter.background:
                    screen.blit(Interpreter.background, (0, 0))
                if "out" in slide.methods:
                    Interpreter.run_block(slide.methods["out"][1], {
                        "time": elapsed,
                        "outtime": out_elapsed
                    })
                Interpreter.draw_objects()
                pygame.display.flip()
                clock.tick(60)

            Interpreter.current_slide_index += 1

        pygame.quit()
        sys.exit()

    @staticmethod
    def draw_objects():
        for name, obj in Interpreter.objects.items():
            if not obj.visible:
                continue
            alpha = int(obj.props.get("opacity", 100) / 100 * 255)
            if obj.type == "text":
                txt = obj.props.get("text", name)
                size = int(obj.props.get("fontSize", 24))
                color = obj.props.get("color", "#ffffff")
                fontname = obj.props.get("font", "Rubik")
                try:
                    font = pygame.font.SysFont(fontname, size)
                except:
                    font = pygame.font.SysFont("Arial", size)
                color = pygame.Color(color)
                surf = font.render(txt, True, color)
                surf.set_alpha(alpha)
                x = screen_width * obj.props.get("positionx", 50) / 100
                y = screen_height * obj.props.get("positiony", 50) / 100
                screen.blit(surf, (x, y))
            elif obj.type == "image" and obj.props.get("surf"):
                surf = obj.props["surf"]
                scale = obj.props.get("scale", 1.0)
                w = surf.get_width()
                h = surf.get_height()
                surf = pygame.transform.scale(surf, (int(w * scale), int(h * scale)))
                surf.set_alpha(alpha)
                x = screen_width * obj.props.get("positionx", 50) / 100
                y = screen_height * obj.props.get("positiony", 50) / 100
                screen.blit(surf, (x, y))

with open("program.txt", "r") as f:
    program = f.readlines()

Interpreter.parse(program)
Interpreter.run()
