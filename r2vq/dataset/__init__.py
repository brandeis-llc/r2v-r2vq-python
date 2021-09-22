import sys


def extract(dataset_fname, out_fname, recipe_ids):
    write = False
    dataset_f = open(dataset_fname, 'r', encoding='utf8')
    if out_fname and len(out_fname) > 0:
        out_f = open(out_fname, 'w', encoding='utf8')
    else:
        out_f = sys.stdout
    for line in dataset_f:
        if "newdoc id" in line:
            if line.strip().split(' = ')[-1] in recipe_ids:
                write = True
            else:
                write = False
        if write:
            out_f.write(line)
                
    dataset_f.close()
    out_f.close()
                