"""PDF sintético estruturalmente válido, sem dependências ou dados pessoais."""
def pdf(message):
    message = message.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    stream = f'BT /F1 12 Tf 20 40 Td ({message}) Tj ET'
    objects = ['<< /Type /Catalog /Pages 2 0 R >>',
               '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 100] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
               f'<< /Length {len(stream.encode("ascii"))} >>\nstream\n{stream}\nendstream',
               '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    content = '%PDF-1.4\n'
    offsets = [0]
    for identity, obj in enumerate(objects, 1):
        offsets.append(len(content.encode('ascii')))
        content += f'{identity} 0 obj\n{obj}\nendobj\n'
    start = len(content.encode('ascii'))
    content += 'xref\n0 6\n0000000000 65535 f \n'
    content += ''.join(f'{offset:010d} 00000 n \n' for offset in offsets[1:])
    return content+f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'
