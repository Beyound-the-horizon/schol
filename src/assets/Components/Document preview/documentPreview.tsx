import { useEffect, useState } from "react";

type DocumentPreviewProps = {
  file: File;
  url: string;
  kind: "image" | "pdf" | "file";
  alt: string;
};

export default function DocumentPreview({
  file,
  url,
  kind,
  alt,
}: DocumentPreviewProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(
    kind === "image" ? url : null
  );

  useEffect(() => {
    if (kind === "image") {
      setPreviewUrl(url);
      return;
    }

    let cancelled = false;
    let generated: string | null = null;

    async function renderFirstPage() {
      if (kind === "pdf" || file.type === "application/pdf") {
        const pdfjs = await import("pdfjs-dist");
        const worker = await import("pdfjs-dist/build/pdf.worker.min.mjs?url");
        pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
        const data = await file.arrayBuffer();
        const pdf = await pdfjs.getDocument({ data }).promise;
        const page = await pdf.getPage(1);
        const viewport = page.getViewport({ scale: 1.4 });
        const canvas = document.createElement("canvas");
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        const context = canvas.getContext("2d");
        if (!context) return;
        await page.render({ canvas, canvasContext: context, viewport }).promise;
        generated = canvas.toDataURL("image/jpeg", 0.82);
        if (!cancelled) setPreviewUrl(generated);
        return;
      }

      const canvas = document.createElement("canvas");
      canvas.width = 228;
      canvas.height = 280;
      const context = canvas.getContext("2d");
      if (!context) return;
      context.fillStyle = "#f4f4f5";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.fillStyle = "#71717a";
      context.font = "13px sans-serif";
      wrapText(context, file.name, 16, 40, 196, 18);
      generated = canvas.toDataURL("image/jpeg", 0.82);
      if (!cancelled) setPreviewUrl(generated);
    }

    void renderFirstPage();
    return () => {
      cancelled = true;
    };
  }, [file, kind, url]);

  if (!previewUrl) {
    return <span className="documentFallback">{file.name}</span>;
  }

  return <img src={previewUrl} alt={alt} />;
}

function wrapText(
  context: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number
) {
  const words = text.split(/\s+/);
  let line = "";
  let offset = y;
  for (const word of words) {
    const test = line ? `${line} ${word}` : word;
    if (context.measureText(test).width > maxWidth) {
      context.fillText(line, x, offset);
      line = word;
      offset += lineHeight;
    } else {
      line = test;
    }
  }
  if (line) context.fillText(line, x, offset);
}
