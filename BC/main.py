import yaml
from jinja2 import Environment, FileSystemLoader

def main():
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)

    # Jinja2 environment setup
    env = Environment(loader=FileSystemLoader('.'))

    # Load template
    template = env.get_template('env.sv.j2')

    output = template.render(config)

    with open("env.sv", "w") as file:
        file.write(output)

    print("env.sv generated successfully.")


if __name__ == "__main__":
    main()
