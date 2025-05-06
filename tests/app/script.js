import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// --- Basic Scene Setup ---
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xeeeeee); // Light grey background

const container = document.getElementById('scene-container');

const camera = new THREE.PerspectiveCamera(
    50, // Field of View
    container.clientWidth / container.clientHeight, // Aspect Ratio
    0.1, // Near clipping plane
    1000 // Far clipping plane
);
camera.position.set(0, 1.5, 4); // Position the camera

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.setPixelRatio(window.devicePixelRatio); // Adjust for high-DPI screens
container.appendChild(renderer.domElement); // Add canvas to the HTML

// --- Lighting ---
const ambientLight = new THREE.AmbientLight(0xffffff, 0.6); // Soft white light
scene.add(ambientLight);

const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0); // Brighter directional light
directionalLight.position.set(5, 10, 7.5);
scene.add(directionalLight);

// --- Controls (for rotating the view) ---
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; // Smooths camera movement
controls.target.set(0, 1, 0); // Point camera towards the center of the model (adjust y)
controls.update();

// --- Load Model ---
const loader = new GLTFLoader();
let model, skeleton, bones = {}; // Variables to hold model, skeleton helper, and bone map

loader.load(
    'models/rigged_human.glb', // Path to your model
    function (gltf) {
        model = gltf.scene;
        scene.add(model);

        // --- Find and Store Bones ---
        // Traverse the model to find bones by name and store them
        model.traverse((object) => {
            if (object.isBone) {
                bones[object.name] = object;
                // console.log("Found bone:", object.name); // Uncomment to see all bone names
            }
        });

        // Optional: Add a SkeletonHelper to visualize the skeleton (for debugging)
        // skeleton = new THREE.SkeletonHelper(model);
        // skeleton.visible = true; // Set to true to see the skeleton
        // scene.add(skeleton);

        console.log('Model loaded successfully. Found bones:', Object.keys(bones));
        setupSliders(); // Setup sliders AFTER the model is loaded

    },
    // called while loading is progressing
    function (xhr) {
        console.log((xhr.loaded / xhr.total * 100) + '% loaded');
    },
    // called when loading has errors
    function (error) {
        console.error('An error happened loading the model:', error);
    }
);

// --- Slider Interaction ---
function setupSliders() {
    const sliders = document.querySelectorAll('#controls input[type="range"]');

    sliders.forEach(slider => {
        const boneName = slider.dataset.bone;
        const axis = slider.dataset.axis; // 'x', 'y', or 'z'
        const valueSpan = slider.nextElementSibling; // Get the span to display the value

        if (!bones[boneName]) {
            console.warn(`Bone named "${boneName}" not found in the model for slider "${slider.id}".`);
            slider.disabled = true; // Disable slider if bone doesn't exist
            return; // Skip this slider
        }

        // Set initial slider value display
        if (valueSpan) {
             valueSpan.textContent = parseFloat(slider.value).toFixed(2);
        }

        slider.addEventListener('input', () => {
            const value = parseFloat(slider.value); // Get slider value as a number
            const targetBone = bones[boneName];

            if (targetBone) {
                // Set rotation on the specified axis
                targetBone.rotation[axis] = value;

                 // Update the displayed value
                 if (valueSpan) {
                    valueSpan.textContent = value.toFixed(2);
                 }

            } else {
                // This check is redundant if the initial check worked, but good practice
                console.warn(`Target bone "${boneName}" became unavailable?`);
            }
        });
    });
}


// --- Handle Window Resize ---
window.addEventListener('resize', () => {
    // Update camera aspect ratio
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();

    // Update renderer size
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
});

// --- Animation Loop ---
function animate() {
    requestAnimationFrame(animate); // Loop

    controls.update(); // Required if enableDamping is true
    renderer.render(scene, camera); // Render the scene
}

// Start the animation loop only if WebGL is supported
if (renderer.domElement) {
     animate();
} else {
    console.error("WebGL not supported or renderer couldn't initialize.");
    // Maybe display a message to the user
}