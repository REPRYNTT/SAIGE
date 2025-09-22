#include <iostream>
#include <unistd.h>
#include <sys/wait.h>
#include <string>

int main() {
    std::string server_cmd = "~/llama.cpp/build/bin/llama-server -m ~/SAIGE/models/Phi-3-mini-4k-instruct-q4.gguf -ngl 99 --host 0.0.0.0 --port 8080 -c 4096 --log-file /var/log/saige_inference.log";

    while (true) {
        pid_t pid = fork();
        if (pid == 0) {
            // Child: Run server
            execl("/bin/sh", "sh", "-c", server_cmd.c_str(), (char *)NULL);
            exit(1);  // If execl fails
        } else if (pid > 0) {
            // Parent: Wait and restart on exit
            int status;
            waitpid(pid, &status, 0);
            std::cerr << "Server exited (code " << WEXITSTATUS(status) << "); restarting in 10s..." << std::endl;
            sleep(10);
        } else {
            std::cerr << "Fork failed" << std::endl;
            return 1;
        }
    }
    return 0;
}
