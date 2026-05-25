// downloadSVG.ts

export function downloadSVG(
  svgElement: SVGSVGElement,
  filename = 'chart.svg'
) {
  const clone = svgElement.cloneNode(true) as SVGSVGElement;
  const viewBox = svgElement.viewBox.baseVal;
  const width = viewBox.width || svgElement.clientWidth;
  const height = viewBox.height || svgElement.clientHeight;

  // white background
  const bg = document.createElementNS(
    'http://www.w3.org/2000/svg',
    'rect'
  );

  bg.setAttribute('x', String(viewBox.x));
  bg.setAttribute('y', String(viewBox.y));
  bg.setAttribute('width', String(width));
  bg.setAttribute('height', String(height));
  bg.setAttribute('fill', 'white');

  clone.insertBefore(bg, clone.firstChild);

  const serializer = new XMLSerializer();
  const source = serializer.serializeToString(clone);

  const blob = new Blob([source], {
    type: 'image/svg+xml;charset=utf-8'
  });

  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();

  URL.revokeObjectURL(url);
}