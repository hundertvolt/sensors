import re, sys, textwrap
# usage: e_rewrap.py <file> <start-line-prefix> <end-line-prefix (exclusive)> <indent> [width]
path, start_prefix, end_prefix, indent = sys.argv[1:5]
width = int(sys.argv[5]) if len(sys.argv) > 5 else 100
lines = open(path).read().split('\n')
start = next(i for i, l in enumerate(lines) if l.startswith(start_prefix))
end = next(i for i in range(start + 1, len(lines)) if (lines[i].strip() == '' if end_prefix == '<blank>' else lines[i].startswith(end_prefix)))
text = ' '.join(l.strip() for l in lines[start:end])
text = re.sub(r'`[^`]*`', lambda m: m.group(0).replace(' ', '\x00'), text)
wrapped = textwrap.wrap(text, width=width, initial_indent=indent, subsequent_indent=indent, break_long_words=False, break_on_hyphens=False)
lines[start:end] = [w.replace('\x00', ' ') for w in wrapped]
open(path, 'w').write('\n'.join(lines))
