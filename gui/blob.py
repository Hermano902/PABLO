"""
Three.js animated point-cloud blob — PABLO's visual identity.

Usage in app.py:
    ui.html(make_blob_container(size, blob_id))     # pure HTML, no scripts
    ui.add_body_html(make_blob_script(size, blob_id))  # JS goes in body

NiceGUI 3.x forbids <script> tags inside ui.html() — they must go via
ui.add_body_html() or ui.add_head_html().

Control signals (callable from Python via ui.run_javascript):
    pablo.blob['main'].setSpeed(1.0)   # idle
    pablo.blob['main'].setSpeed(3.0)   # initialising
    pablo.blob['main'].pulse()         # single brightness spike
"""


def make_blob_container(size: int = 300, blob_id: str = "main") -> str:
    """Pure HTML container (no scripts). Safe for ui.html()."""
    return (
        f'<div id="pablo-blob-{blob_id}" '
        f'style="width:{size}px;height:{size}px;flex-shrink:0;'
        f'display:flex;align-items:center;justify-content:center;">'
        f'<canvas id="pablo-blob-canvas-{blob_id}" '
        f'width="{size}" height="{size}" '
        f'style="display:block;width:{size}px!important;height:{size}px!important;'
        f'flex-shrink:0;"></canvas>'
        f'</div>'
    )


def make_blob_script(size: int = 300, blob_id: str = "main") -> str:
    """
    Self-contained <script> block. Add via ui.add_body_html().
    Retries until both Three.js and the canvas are available.
    """
    dot_size = round(size * 0.000065, 6)
    return f"""
<script>
(function() {{
  function init() {{
    var canvas = document.getElementById('pablo-blob-canvas-{blob_id}');
    if (!canvas || typeof THREE === 'undefined') {{
      setTimeout(init, 50);
      return;
    }}

    var SIZE = {size};
    var scene = new THREE.Scene();
    var cam   = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
    cam.position.z = 3.5;

    var renderer = new THREE.WebGLRenderer({{ canvas: canvas, antialias: true, alpha: true, preserveDrawingBuffer: true }});
    renderer.setSize(SIZE, SIZE);
    renderer.setPixelRatio(1);
    renderer.setClearColor(0x000000, 0);

    // Re-render on context restore (happens on window resize/maximize in native mode)
    canvas.addEventListener('webglcontextlost',    function(e) {{ e.preventDefault(); }}, false);
    canvas.addEventListener('webglcontextrestored', function()  {{ renderer.setSize(SIZE, SIZE); }}, false);

    var geo     = new THREE.SphereGeometry(1, 64, 64);
    var origPos = new Float32Array(geo.attributes.position.array);
    var count   = geo.attributes.position.count;

    var colArr = new Float32Array(count * 3);
    geo.setAttribute('color', new THREE.BufferAttribute(colArr, 3));

    var mat = new THREE.PointsMaterial({{
      size:            {dot_size},
      vertexColors:    true,
      blending:        THREE.AdditiveBlending,
      transparent:     true,
      depthWrite:      false,
      sizeAttenuation: true
    }});

    var pts = new THREE.Points(geo, mat);
    scene.add(pts);

    var time       = 0;
    var speed      = 0.008;
    var brightness = 1.0;
    var pulsing    = false;

    function noise(x, y, z, t) {{
      return (
        Math.sin(x*2.3 + t*1.1) * Math.cos(y*1.9 + t*0.7) * Math.sin(z*2.1 + t*0.9) +
        Math.sin(x*1.1 + t*0.5) * Math.cos(z*1.3 + t*0.8) * 0.5
      ) / 1.5;
    }}

    function animate() {{
      requestAnimationFrame(animate);
      time += speed;

      var pos = geo.attributes.position;
      var col = geo.attributes.color;

      for (var i = 0; i < count; i++) {{
        var ox = origPos[i*3], oy = origPos[i*3+1], oz = origPos[i*3+2];
        var n  = noise(ox, oy, oz, time) * 0.35;
        var r  = 1.0 + n;
        pos.array[i*3]   = ox * r;
        pos.array[i*3+1] = oy * r;
        pos.array[i*3+2] = oz * r;
        var t = Math.max(0, Math.min(1, (n + 0.35) / 0.70));
        var b = brightness;
        col.array[i*3]   = (t < 0.3 ? 0.25*(1-t/0.3) : 0.0) * b;
        col.array[i*3+1] = (0.35 + t*0.55) * b;
        col.array[i*3+2] = (0.60 + t*0.40) * b;
      }}
      pos.needsUpdate = true;
      col.needsUpdate = true;
      pts.rotation.y += 0.004;
      pts.rotation.x += 0.001;
      if (pulsing) {{
        brightness = Math.min(brightness + 0.08, 2.5);
        if (brightness >= 2.5) pulsing = false;
      }} else {{
        brightness = Math.max(brightness - 0.015, 1.0);
      }}
      renderer.render(scene, cam);
    }}

    animate();

    window.pablo      = window.pablo      || {{}};
    window.pablo.blob = window.pablo.blob || {{}};
    window.pablo.blob['{blob_id}'] = {{
      setSpeed: function(s) {{ speed = s * 0.008; }},
      pulse:    function()  {{ pulsing = true; }}
    }};
  }}

  init();
}})();
</script>
"""


# Three.js CDN — added once to <head> in app.py via ui.add_head_html.
# 'async' prevents render-blocking: the blob script retries via setTimeout
# until THREE is defined, so load order doesn't matter.
THREE_JS_HEAD = (
    '<script async src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r134/three.min.js">'
    '</script>'
)
