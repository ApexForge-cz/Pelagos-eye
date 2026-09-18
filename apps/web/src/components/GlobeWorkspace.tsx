import { useEffect, useRef, useState, type MutableRefObject } from 'react'
import {
  AdditiveBlending,
  AmbientLight,
  BackSide,
  BufferGeometry,
  CanvasTexture,
  Color,
  DirectionalLight,
  Float32BufferAttribute,
  Group,
  Line,
  LineBasicMaterial,
  Material,
  Mesh,
  MeshBasicMaterial,
  MeshPhongMaterial,
  PerspectiveCamera,
  Points,
  PointsMaterial,
  Raycaster,
  Scene,
  ShaderMaterial,
  SphereGeometry,
  Sprite,
  SpriteMaterial,
  SRGBColorSpace,
  TextureLoader,
  Texture,
  Vector2,
  Vector3,
  WebGLRenderer,
  type Object3D,
} from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

import type { EarthquakeRecord, PortRecord, ViewportBounds } from '../api/spatial'
import type { MapSelection } from './MapWorkspace'

interface GlobeWorkspaceProps {
  ports: PortRecord[]
  earthquakes: EarthquakeRecord[]
  portsVisible: boolean
  earthquakesVisible: boolean
  inspectMarine: boolean
  onBoundsChange: (bounds: ViewportBounds) => void
  onSelection: (selection: MapSelection) => void
  onUnavailable: () => void
}

interface BoundaryCollection {
  features?: Array<{
    geometry?: {
      type?: string
      coordinates?: unknown
    }
  }>
}

const EARTH_RADIUS = 1
const INITIAL_LONGITUDE = 105
const GLOBAL_BOUNDS: ViewportBounds = { west: -180, south: -85, east: 180, north: 85 }

export function GlobeWorkspace({
  ports,
  earthquakes,
  portsVisible,
  earthquakesVisible,
  inspectMarine,
  onBoundsChange,
  onSelection,
  onUnavailable,
}: GlobeWorkspaceProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<Scene | null>(null)
  const globeRef = useRef<Group | null>(null)
  const rendererRef = useRef<WebGLRenderer | null>(null)
  const cameraRef = useRef<PerspectiveCamera | null>(null)
  const markersRef = useRef<Group | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const callbacksRef = useRef({ onSelection, onUnavailable })
  const recordsRef = useRef({ ports, earthquakes, portsVisible, earthquakesVisible })
  const inspectMarineRef = useRef(inspectMarine)
  const [coordinates, setCoordinates] = useState(`${INITIAL_LONGITUDE.toFixed(2)}°, 20.00°`)
  const [motionStopped, setMotionStopped] = useState(false)
  const [reducedMotion] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )

  useEffect(() => {
    callbacksRef.current = { onSelection, onUnavailable }
  }, [onSelection, onUnavailable])

  useEffect(() => {
    recordsRef.current = { ports, earthquakes, portsVisible, earthquakesVisible }
    if (sceneRef.current && globeRef.current) {
      replaceMarkers(sceneRef.current, globeRef.current, markersRef, recordsRef.current)
    }
  }, [earthquakes, earthquakesVisible, ports, portsVisible])

  useEffect(() => {
    inspectMarineRef.current = inspectMarine
  }, [inspectMarine])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let renderer: WebGLRenderer
    try {
      renderer = new WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance',
      })
    } catch {
      callbacksRef.current.onUnavailable()
      return
    }
    if (!renderer.capabilities.isWebGL2) {
      renderer.dispose()
      callbacksRef.current.onUnavailable()
      return
    }

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75))
    renderer.setSize(container.clientWidth, container.clientHeight, false)
    renderer.outputColorSpace = SRGBColorSpace
    renderer.domElement.className = 'globe-canvas'
    renderer.domElement.setAttribute('aria-label', 'OceanScope 交互式三维地球')
    container.append(renderer.domElement)
    rendererRef.current = renderer

    const scene = new Scene()
    sceneRef.current = scene
    const camera = new PerspectiveCamera(
      38,
      container.clientWidth / container.clientHeight,
      0.01,
      100,
    )
    camera.position.set(0, 0.2, 3.6)
    cameraRef.current = camera

    const globe = new Group()
    globe.rotation.y = degreesToRadians(-INITIAL_LONGITUDE)
    scene.add(globe)
    globeRef.current = globe

    scene.add(new AmbientLight(0x7aa9c6, 1.25))
    const keyLight = new DirectionalLight(0xd7f1ff, 2.8)
    keyLight.position.set(-2.5, 1.8, 3.5)
    scene.add(keyLight)
    const rimLight = new DirectionalLight(0x2c72ff, 1.8)
    rimLight.position.set(3, -1, -2)
    scene.add(rimLight)

    const earthMaterial = new MeshPhongMaterial({
      color: 0x7c9bb4,
      emissive: new Color(0x051526),
      emissiveIntensity: 0.72,
      shininess: 12,
      specular: new Color(0x163b55),
    })
    const earth = new Mesh(new SphereGeometry(EARTH_RADIUS, 96, 64), earthMaterial)
    earth.name = 'earth-surface'
    globe.add(earth)

    const textureLoader = new TextureLoader()
    textureLoader.load(
      '/assets/land_ocean_ice_2048.png',
      (texture) => {
        texture.colorSpace = SRGBColorSpace
        earthMaterial.map = texture
        earthMaterial.needsUpdate = true
      },
      undefined,
      () => callbacksRef.current.onUnavailable(),
    )

    const atmosphere = new Mesh(
      new SphereGeometry(EARTH_RADIUS * 1.09, 64, 48),
      new ShaderMaterial({
        transparent: true,
        side: BackSide,
        blending: AdditiveBlending,
        depthWrite: false,
        uniforms: {
          glowColor: { value: new Color(0x54c9ff) },
          intensity: { value: 0.7 },
        },
        vertexShader: `
          varying vec3 vNormal;
          varying vec3 vView;
          void main() {
            vec4 worldPosition = modelMatrix * vec4(position, 1.0);
            vNormal = normalize(mat3(modelMatrix) * normal);
            vView = normalize(cameraPosition - worldPosition.xyz);
            gl_Position = projectionMatrix * viewMatrix * worldPosition;
          }
        `,
        fragmentShader: `
          uniform vec3 glowColor;
          uniform float intensity;
          varying vec3 vNormal;
          varying vec3 vView;
          void main() {
            float rim = pow(1.0 - abs(dot(vNormal, vView)), 3.1);
            gl_FragColor = vec4(glowColor, rim * intensity);
          }
        `,
      }),
    )
    scene.add(atmosphere)

    const stars = createStars()
    scene.add(stars)

    const boundaryController = new AbortController()
    void loadBoundaries(globe, boundaryController.signal)
    replaceMarkers(scene, globe, markersRef, recordsRef.current)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.055
    controls.enablePan = false
    controls.minDistance = 1.55
    controls.maxDistance = 5.2
    controls.autoRotate = !reducedMotion
    controls.autoRotateSpeed = 0.32
    controlsRef.current = controls

    const stopAutomaticMotion = () => {
      controls.autoRotate = false
      setMotionStopped(true)
    }
    controls.addEventListener('start', stopAutomaticMotion)

    const raycaster = new Raycaster()
    const pointer = new Vector2()
    const setPointer = (event: PointerEvent) => {
      const bounds = renderer.domElement.getBoundingClientRect()
      pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1
      pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1
      raycaster.setFromCamera(pointer, camera)
    }
    const handlePointerMove = (event: PointerEvent) => {
      setPointer(event)
      const marker = firstSelectable(
        raycaster.intersectObjects(markersRef.current?.children ?? [], true),
      )
      renderer.domElement.style.cursor = marker
        ? 'pointer'
        : inspectMarineRef.current
          ? 'crosshair'
          : 'grab'
      const hit = raycaster.intersectObject(earth, false)[0]
      if (!hit) return
      const local = globe.worldToLocal(hit.point.clone()).normalize()
      const { longitude, latitude } = vectorToLonLat(local)
      setCoordinates(`${longitude.toFixed(2)}°, ${latitude.toFixed(2)}°`)
    }
    const handleClick = (event: PointerEvent) => {
      setPointer(event)
      const marker = firstSelectable(
        raycaster.intersectObjects(markersRef.current?.children ?? [], true),
      )
      const selection = marker?.userData.selection as MapSelection | undefined
      if (selection) {
        callbacksRef.current.onSelection(selection)
        return
      }
      if (!inspectMarineRef.current) return
      const hit = raycaster.intersectObject(earth, false)[0]
      if (!hit) return
      const { longitude, latitude } = vectorToLonLat(
        globe.worldToLocal(hit.point.clone()).normalize(),
      )
      callbacksRef.current.onSelection({ kind: 'coordinate', longitude, latitude })
    }
    renderer.domElement.addEventListener('pointermove', handlePointerMove)
    renderer.domElement.addEventListener('click', handleClick)

    const resizeObserver = new ResizeObserver(() => {
      const width = container.clientWidth
      const height = container.clientHeight
      if (width === 0 || height === 0) return
      camera.aspect = width / height
      camera.updateProjectionMatrix()
      renderer.setSize(width, height, false)
    })
    resizeObserver.observe(container)

    let animationFrame = 0
    const render = () => {
      controls.update()
      renderer.render(scene, camera)
      animationFrame = window.requestAnimationFrame(render)
    }
    render()
    onBoundsChange(GLOBAL_BOUNDS)

    return () => {
      boundaryController.abort()
      window.cancelAnimationFrame(animationFrame)
      resizeObserver.disconnect()
      renderer.domElement.removeEventListener('pointermove', handlePointerMove)
      renderer.domElement.removeEventListener('click', handleClick)
      controls.removeEventListener('start', stopAutomaticMotion)
      controls.dispose()
      disposeObject(scene)
      renderer.dispose()
      renderer.domElement.remove()
      sceneRef.current = null
      globeRef.current = null
      rendererRef.current = null
      cameraRef.current = null
      markersRef.current = null
      controlsRef.current = null
    }
  }, [onBoundsChange, reducedMotion])

  const resetView = () => {
    const camera = cameraRef.current
    const controls = controlsRef.current
    const globe = globeRef.current
    if (!camera || !controls || !globe) return
    camera.position.set(0, 0.2, 3.6)
    globe.rotation.set(0, degreesToRadians(-INITIAL_LONGITUDE), 0)
    controls.target.set(0, 0, 0)
    controls.update()
  }

  return (
    <div
      className={`globe-stage ${inspectMarine ? 'is-inspecting' : ''}`}
      data-motion={reducedMotion ? 'reduced' : 'animated'}
    >
      <div ref={containerRef} className="globe-renderer" />
      <div className="globe-horizon" aria-hidden="true" />
      <div className="globe-mode-state">
        <span className="status-dot" /> 3D EARTH · WGS 84
      </div>
      {motionStopped && <div className="globe-motion-state">AUTO ROTATION PAUSED</div>}
      <button className="globe-reset" type="button" onClick={resetView}>
        重置视角
      </button>
      <div className="coordinate-readout" aria-live="off">
        WGS 84&nbsp; {coordinates}
      </div>
      <p className="globe-attribution">
        Earth imagery: NASA Visible Earth · Boundaries: Natural Earth · Visual context only
      </p>
    </div>
  )
}

function replaceMarkers(
  scene: Scene,
  globe: Group,
  markersRef: MutableRefObject<Group | null>,
  records: Pick<
    GlobeWorkspaceProps,
    'ports' | 'earthquakes' | 'portsVisible' | 'earthquakesVisible'
  >,
) {
  if (markersRef.current) {
    globe.remove(markersRef.current)
    disposeObject(markersRef.current)
  }
  const markers = new Group()
  markers.name = 'spatial-markers'
  const portGlow = records.portsVisible ? createGlowTexture('#76d6dc') : null
  const eventGlow = records.earthquakesVisible ? createGlowTexture('#ff7b68') : null

  if (records.portsVisible) {
    for (const record of records.ports) {
      if (record.longitude === null || record.latitude === null) continue
      markers.add(
        createMarker(
          record.longitude,
          record.latitude,
          0x76d6dc,
          portGlow!,
          { kind: 'port', record },
          0.014,
        ),
      )
    }
  }
  if (records.earthquakesVisible) {
    for (const record of records.earthquakes) {
      markers.add(
        createMarker(
          record.longitude,
          record.latitude,
          0xff7b68,
          eventGlow!,
          { kind: 'earthquake', record },
          Math.min(0.026, 0.014 + (record.magnitude ?? 0) * 0.0018),
        ),
      )
    }
  }
  globe.add(markers)
  markersRef.current = markers
  scene.updateMatrixWorld(true)
}

function createMarker(
  longitude: number,
  latitude: number,
  color: number,
  glowTexture: CanvasTexture,
  selection: MapSelection,
  radius: number,
) {
  const marker = new Group()
  marker.position.copy(lonLatToVector(longitude, latitude, EARTH_RADIUS * 1.018))
  marker.userData.selection = selection
  const core = new Mesh(
    new SphereGeometry(radius, 12, 8),
    new MeshBasicMaterial({ color, toneMapped: false }),
  )
  core.userData.selection = selection
  marker.add(core)
  const halo = new Sprite(
    new SpriteMaterial({ map: glowTexture, transparent: true, depthWrite: false, opacity: 0.72 }),
  )
  halo.scale.setScalar(radius * 6.5)
  halo.userData.selection = selection
  marker.add(halo)
  return marker
}

function createGlowTexture(color: string) {
  const canvas = document.createElement('canvas')
  canvas.width = 64
  canvas.height = 64
  const context = canvas.getContext('2d')
  if (context) {
    const gradient = context.createRadialGradient(32, 32, 1, 32, 32, 31)
    gradient.addColorStop(0, '#ffffff')
    gradient.addColorStop(0.16, color)
    gradient.addColorStop(0.45, `${color}88`)
    gradient.addColorStop(1, `${color}00`)
    context.fillStyle = gradient
    context.fillRect(0, 0, 64, 64)
  }
  return new CanvasTexture(canvas)
}

function createStars() {
  const positions: number[] = []
  for (let index = 0; index < 650; index += 1) {
    const y = 1 - (index / 649) * 2
    const radius = Math.sqrt(1 - y * y)
    const angle = index * 2.399963229728653
    const distance = 7 + ((index * 37) % 100) / 45
    positions.push(
      Math.cos(angle) * radius * distance,
      y * distance,
      Math.sin(angle) * radius * distance,
    )
  }
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new Float32BufferAttribute(positions, 3))
  const material = new PointsMaterial({
    color: 0x7ea9c3,
    size: 0.018,
    transparent: true,
    opacity: 0.58,
    sizeAttenuation: true,
  })
  return new Points(geometry, material)
}

async function loadBoundaries(globe: Group, signal: AbortSignal) {
  try {
    const response = await fetch('/assets/ne_110m_admin_0_countries.geojson', { signal })
    if (!response.ok) return
    const collection = (await response.json()) as BoundaryCollection
    if (signal.aborted) return
    const material = new LineBasicMaterial({
      color: 0x7fd4e6,
      transparent: true,
      opacity: 0.26,
      depthWrite: false,
    })
    const boundaries = new Group()
    boundaries.name = 'country-boundaries'
    for (const feature of collection.features ?? []) {
      for (const ring of geometryRings(feature.geometry?.type, feature.geometry?.coordinates)) {
        const points = ring.flatMap((coordinate) => {
          const longitude = coordinate[0]
          const latitude = coordinate[1]
          return longitude === undefined || latitude === undefined
            ? []
            : [lonLatToVector(longitude, latitude, EARTH_RADIUS * 1.002)]
        })
        if (points.length > 1)
          boundaries.add(new Line(new BufferGeometry().setFromPoints(points), material))
      }
    }
    globe.add(boundaries)
  } catch {
    // Boundaries are optional visual context; the textured globe and data remain usable.
  }
}

function geometryRings(type: string | undefined, coordinates: unknown): number[][][] {
  if (!Array.isArray(coordinates)) return []
  if (type === 'Polygon') return coordinates as number[][][]
  if (type === 'MultiPolygon') return (coordinates as number[][][][]).flat()
  return []
}

function lonLatToVector(longitude: number, latitude: number, radius: number) {
  const longitudeRadians = degreesToRadians(longitude)
  const latitudeRadians = degreesToRadians(latitude)
  const latitudeRadius = Math.cos(latitudeRadians) * radius
  return new Vector3(
    latitudeRadius * Math.sin(longitudeRadians),
    Math.sin(latitudeRadians) * radius,
    latitudeRadius * Math.cos(longitudeRadians),
  )
}

function vectorToLonLat(vector: Vector3) {
  return {
    longitude: radiansToDegrees(Math.atan2(vector.x, vector.z)),
    latitude: radiansToDegrees(Math.asin(vector.y)),
  }
}

function firstSelectable(intersections: Array<{ object: Object3D }>) {
  return intersections.find(({ object }) => object.userData.selection)?.object
}

function disposeObject(object: Object3D) {
  object.traverse((child) => {
    const disposable = child as Object3D & {
      geometry?: BufferGeometry
      material?: Material | Material[]
    }
    disposable.geometry?.dispose()
    if (disposable.material) {
      const materials = Array.isArray(disposable.material)
        ? disposable.material
        : [disposable.material]
      for (const material of materials) {
        const texture = (material as Material & { map?: Texture | null }).map
        texture?.dispose()
        material.dispose()
      }
    }
  })
}

function degreesToRadians(value: number) {
  return (value * Math.PI) / 180
}

function radiansToDegrees(value: number) {
  return (value * 180) / Math.PI
}
