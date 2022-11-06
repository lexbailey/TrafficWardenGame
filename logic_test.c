/*

This is a model of the car movement logic
The model can be checked with CBMC:

    cbmc logic_test.c --trace

I used this to find the bug in the logic where a car would sometimes move without updating the grid state.
Perhaps I should have chosen a different representation, where there was only one source of truth
instead I chose to use FM, because I'm a FM person :)

anyway, leaving this here in case I need it again later

*/
#include <stdio.h>


#define UP (1)
#define DOWN (2)
#define LEFT (3)
#define RIGHT (4)

#define SIZE (3)

#define XY(x,y) ((y*SIZE)+(x))

#define NONE (-1)

void clamp(int *x, int *y){
    if (*x < 0){*x = 0;}
    if (*y < 0){*y = 0;}
    if (*x >= SIZE){*x = SIZE-1;}
    if (*y >= SIZE){*y = SIZE-1;}
}

int reflect(int d){
    switch (d){
        case UP: return DOWN;
        case DOWN: return UP;
        case LEFT: return RIGHT;
        case RIGHT: return LEFT;
    }
    return -1;
}

void move(int *x, int *y, int dir){
    switch (dir){
        case UP: *y += 1; break;
        case DOWN:*y -= 1; break;
        case LEFT: *x -=1; break;
        case RIGHT: *x +=1; break;
    }
}

typedef struct{
    int tile;
    int car;
}cell;

cell arena[SIZE*SIZE];

int playerx = 0;
int playery = 0;
int player_dir = UP;

int nondet_int();

void init_player(){
    playerx = nondet_int();
    playery = nondet_int();
    player_dir = nondet_int();
    __CPROVER_assume(playerx >=0);
    __CPROVER_assume(playery >=0);
    __CPROVER_assume(playerx < SIZE);
    __CPROVER_assume(playery < SIZE);
    __CPROVER_assume(
        (player_dir == UP)
        ||(player_dir == DOWN)
        ||(player_dir == LEFT)
        ||(player_dir == RIGHT)
    );
}

void init_arena(){
    for (int x = 0; x <= SIZE-1; x++){
        for (int y = 0; y <= SIZE-1; y++){
            int t = nondet_int();
            __CPROVER_assume(
                (t == UP)
                ||(t == DOWN)
                ||(t == LEFT)
                ||(t == RIGHT)
                ||(t == NONE)
            );
            arena[XY(x,y)].tile = t;
            arena[XY(x,y)].car = NONE;
        }
    }
    arena[XY(playerx, playery)].car = 1;
    int xy = nondet_int();
    __CPROVER_assume(xy < SIZE*SIZE);
    __CPROVER_assume(arena[xy].car == NONE);
    arena[xy].car = 2;
    int xy2 = nondet_int();
    __CPROVER_assume(xy < SIZE*SIZE);
    __CPROVER_assume(arena[xy2].car == NONE);
    arena[xy2].car = 3;
}

/*
    def step_player(self, player_id):
        p = player_id
        player = self.players[p]
        (xy, dir_) = player.get_pos()
        cell = self.get_cell(xy)
        newdir = dir_
        if cell.tile is not None:
            newdir = cell.tile
        dirname, dirfun = newdir
        newxy = Dir.clamp(dirfun(xy), 9)
        if newxy == xy:
            newdir = Dir.reflect(newdir)
            dirname, dirfun = newdir
            newxy = Dir.clamp(dirfun(xy), 9)
        oldcell = self.get_cell(xy)
        newcell = self.get_cell(newxy)
        if newcell.car is None:
            player.set_pos((newxy, newdir))
            newcell.set_car(player)
            oldcell.set_car(None)
        else:
            newdir = Dir.reflect(newdir)
            dirname, dirfun = newdir
            newxy = Dir.clamp(dirfun(xy), 9)
            newcell = self.get_cell(newxy)
            if newcell.car is None:
                player.set_pos((newxy, newdir))
                newcell.set_car(player)
                oldcell.set_car(None)

        if newcell.tile is not None:
            player.set_pos((newxy, newcell.tile))
        if player.has_reached_goal():
            player.add_score(1)
            newcell.clear_goal()
            self.assign_one_goal(player)
*/

int main(){
    init_player();
    init_arena();
    cell c = arena[XY(playerx, playery)]; // { .tile=-1, .car=1 }
    int new_dir = player_dir; // 2 (down)

    if (c.tile != NONE){ // false
        new_dir = c.tile;
    }

    int newx = playerx; // 0
    int newy = playery; // 1
    move(&newx, &newy, new_dir); // newy = 0
    clamp(&newx, &newy);
    if (newx == playerx && newy == playery){ // False
        new_dir = reflect(new_dir);
        newx = playerx;
        newy = playery;
        move(&newx, &newy, new_dir);
        clamp(&newx, &newy);
    }

    cell *oldcell = arena + XY(playerx, playery); // { .tile=-1, .car=1 }
    cell *newcell = arena + XY(newx, newy); // { .tile=-1, .car=2 }

    if (newcell->car == NONE){ // False
        playerx = newx;
        playery = newy;
        player_dir = new_dir;
        newcell->car = 1;
        oldcell->car = NONE;
    }
    else{
        new_dir = reflect(new_dir); // 1 (up)
        newx = playerx; // 0
        newy = playery; // 1
        move(&newx, &newy, new_dir); // newy = 2
        clamp(&newx, &newy);
        newcell = arena + XY(newx, newy); // { .tile=-1, .car=-1 }
        if (newcell->car == NONE){ // True
            playerx = newx; // 0
            playery = newy; // 2
            player_dir = new_dir; // 1
            newcell->car = 1;
            oldcell->car = NONE; //------------------
        }
        else{ // This is what was missing, adding this fixed it
            newx = playerx;
            newy = playery;
            newcell = oldcell;
        }
    }
    if (newcell->tile != NONE){ // False
        playerx = newx;
        playery = newy;
        player_dir = newcell->tile;
    }

    int some_xy = nondet_int(); // 4 (XY(0,1))
    __CPROVER_assume(some_xy >= 0 && some_xy < SIZE*SIZE && some_xy != XY(playerx, playery));
    __CPROVER_assert(arena[some_xy].car != 1, "There is no player car where the player isn't");
    __CPROVER_assert(arena[XY(playerx, playery)].car == 1, "There is a player car where the player is");
}
