#ifndef CAMERA_H
#define CAMERA_H

#include <chrono>
#include <vector>
#include <thread>
#include <atomic>
#include "hittable.h"
#include "material.h"

class camera {
public:
    double  aspect_ratio        = 1.0;  // Ratio of image width over height
    int     image_width         = 100;  // Rendered image width pixel count
    int     samples_per_pixel   = 10;   // Count of random samples per pixel
    int     max_depth           = 10;   // Maximum number of ray bounces into scene
    int     threads             = 0;    // 0 means to use all cores

    double  vfov        = 90;              // Vertical view angle (field of view)
    point3  lookfrom    = point3(0,0,0);   // The point camera is looking from (origin)
    point3  lookat      = point3(0,0,-1);  // point camera is looking at
    vec3    vup         = vec3(0,1,0);     // Camera-relative "up" direction

    double defocus_angle = 0;   // Variation of angle rays through each pixel
    double focus_dist    = 10;  // Distance from camera lookfrom point to perfect focus

    /* Public Camera parameters here */
    void render(const hittable& world) {
        
        initialize();
        std::vector<color> frambuffer(image_height *image_width);

        auto t0 = std::chrono::steady_clock::now();

        int nthreads = (threads > 0) ? threads : int(std::thread::hardware_concurrency());
        if (nthreads < 1) nthreads = 1;

        std::atomic<int> next_row{0};
        std::atomic<int> rows_done{0};

        auto worker = [&]() {
            while (true)
            {
                int j = next_row.fetch_add(1);
                if (j >= image_height)return;

                for (int i = 0; i < image_width; i++) {
                    color pixel_color(0,0,0);
                    for (int sample = 0; sample < samples_per_pixel; sample++) 
                        pixel_color += ray_color(get_ray(i, j), max_depth, world);
                    frambuffer[j * image_width + i] = pixel_samples_scale * pixel_color;
                }
                int done = rows_done.fetch_add(1) + 1;
                if (done % 25 == 0 || done == image_height)
                    std::clog << "\rRows Done: " << done << '/' << image_height << std::flush;
            }
        };
        
        std::vector<std::thread> pool;      //thread pool
        for (int t = 0; t < nthreads; t++)
            pool.emplace_back(worker);      // hire workers

        for(auto& th : pool)
            th.join();                      //wait until workers are done (join them)
    
        auto t1 = std::chrono::steady_clock::now();

        std::cout<< "P3\n" << image_width << ' ' << image_height << "\n255\n";

        // Serialize memory to file
        for (const auto& px : frambuffer)
            write_color(std::cout, px);
        auto t2 = std::chrono::steady_clock::now();
        std::chrono::duration<double> compute_s = t1 - t0;
        std::chrono::duration<double> write_s = t2 - t1;
        std::clog << "\rDone. Compute time: " << compute_s.count()
                  << "s    Write: " << write_s.count() << "s        \n";
    }

private:
    /*Private camera variables here */
    int     image_height;           // Rendered Image height
    double  pixel_samples_scale;    // Color scale factor for a sum of pixel samples
    point3  center;                 // Camera center
    point3  pixel00_loc;            // Location of pixel 0,0
    vec3    pixel_delta_u;          // Offset of pixel to right
    vec3    pixel_delta_v;          // Offset of pixel below
    vec3    u, v, w;                // Camera frame basis vectors
    vec3    defocus_disk_u;         // Defocus disk horizontal radius
    vec3    defocus_disk_v;         // Defocus disk vertical radius

    
    void initialize() {
        image_height = int(image_width / aspect_ratio);
        image_height = (image_height < 1) ? 1 : image_height;

        pixel_samples_scale = 1.0 / samples_per_pixel;
        center = lookfrom;

        //Determining viewport dimensions:
        
        auto theta = degrees_to_radians(vfov);
        auto h = std::tan(theta/2);
        auto viewport_height = 2 * h * focus_dist;
        auto viewport_width = viewport_height * (double(image_width)/image_height);

        // Calculate the u,v,w basis vectors for the camera coordinate frame
        w = unit_vector(lookfrom - lookat);
        u = unit_vector(cross(vup, w));
        v = cross(w, u);

        //Calculate vectors across horizontal and down vertical
        vec3 viewport_u = viewport_width * u;  // Vu Vector --> L to R
        vec3 viewport_v = viewport_height * -v; // Vv Vector --> Top to bottom

        // Calculate the horizontal and vertical delta vectors from pixel to pixel
        pixel_delta_u = viewport_u / image_width;
        pixel_delta_v = viewport_v / image_height;

        // Location of upper left (0,0) pixel 
        auto viewport_upper_left = center - (focus_dist * w) - viewport_u/2 - viewport_v/2;
        pixel00_loc = viewport_upper_left + 0.5 * (pixel_delta_u + pixel_delta_v);

        // Calculate the camera defocus disk basis vectors
        auto defocus_radius = focus_dist * std::tan(degrees_to_radians(defocus_angle / 2));
        defocus_disk_u = u * defocus_radius;
        defocus_disk_v = v * defocus_radius;

    }

    ray get_ray(int i, int j) const {
        // Constructing a camera ray originating from the defocus disk and directed it 
        // to the randomly sampled point around the pixel location (i, j).

        auto offset       = sample_square();
        auto pixel_sample = pixel00_loc
                            + ((i + offset.x()) * pixel_delta_u)
                            + ((j + offset.y()) * pixel_delta_v);

        auto ray_origin = (defocus_angle <= 0) ? center : defocus_disk_sample();
        auto ray_direction = pixel_sample - ray_origin;

        return ray(ray_origin, ray_direction);
    }

    // made for squared pixels
    vec3 sample_square() const{
        // Returns the random vector in the [-0.5, -0.5] and [+0.5, +0.5] unit square
        return vec3(random_double() - 0.5, random_double() - 0.5, 0);
    }

    point3 defocus_disk_sample() const{
        // Returns a random point in the camera defocus disk
        auto p = random_unit_in_disk();
        return center + (p[0] * defocus_disk_u) + (p[1] * defocus_disk_v);

    }

    color ray_color(const ray& r, int depth, const hittable& world) const {
        // If ray bounce is exceeded, no more light is gathered
        if (depth <= 0)
            return color(0,0,0);

        hit_record rec;

        if (world.hit(r, interval(0.001, infinity), rec)) {
            ray scattered;
            color attenuation;
            if (rec.mat->scatter(r, rec, attenuation, scattered)) {
                return attenuation * ray_color(scattered, depth-1, world);
            }
            return color(0,0,0);
        }

        vec3 unit_direction = unit_vector(r.direction());
        auto a = 0.5*(unit_direction.y() + 1.0);
        return (1.0-a)*color(1.0, 1.0, 1.0) + a*color(0.5, 0.7, 1.0);
    }
};

#endif