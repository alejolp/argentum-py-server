# -*- coding: utf-8 -*-

"""
    AONX Server - Pequeño servidor de Argentum Online.
    Copyright (C) 2011 Alejandro Santos <alejolp@alejolp.com.ar>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

__all__ = ['CommandsDecoderException', 'CriticalDecoderException', \
    'ClientCommandsDecoder', 'ServerCommandsEncoder']

import time

from bytequeue import ByteQueue, ByteQueueError, ByteQueueInsufficientData
from aoprotocol import clientPackets, serverPackets, clientPacketsFlip
from util import debug_print
from gamerules import *
from player import Player
import aoprotocol
import corevars as cv

class CommandsDecoderException(Exception):
    """Faltan datos para decodificar un comando del cliente"""
    pass

class CriticalDecoderException(Exception):
    """Error critico en los datos del cliente; cerrar la conexion"""
    pass

class ClientCommandsDecoder(object):
    """Conjunto de funciones para decodificar los datos que envia un cliente"""

    def __init__(self):
        self.cmds = [None] * (aoprotocol.lastClientPacketID + 1)

        for cmdName, cmdId in clientPackets.items():
            self.cmds[cmdId] = getattr(self, "handleCmd" + cmdName, None)

        missingHandlers = [x for x in dir(self) if x.startswith("handleCmd") \
            and getattr(self, x) not in self.cmds]

        if len(missingHandlers) > 0:
            print "Error critico: handlers no utilizados: ", missingHandlers
            assert False

    def handleData(self, prot):
        buf = prot._ao_inbuff
        
        """
        Los comandos consumen los bytes del buffer de entrada, si faltan
        datos se dispara un CommandsDecoderException o ByteQueueError.
        """

        try:
            try:
                while len(buf) > 0:
                    cmd = buf.peekInt8()

                    if cmd < 0 or cmd >= len(self.cmds):
                        debug_print("cmd out of range:", cmd)
                        raise CriticalDecoderException()

                    if self.cmds[cmd] is None:
                        debug_print("cmd not implemented:", cmd, \
                            "should be:", clientPacketsFlip.get(cmd, '?'))
                        raise CriticalDecoderException()

                    # Marca la posicion actual por si hay que hacer rollback.
                    buf.mark()

                    # Invoca al handler del comando cmd.
                    self.cmds[cmd](prot, buf)


                # La operacion commit() destruye los datos del buffer,
                # por lo que para llamarla tengo que estar seguro
                # que se leyeron todos los datos del comando actual.
                #
                # Llamarla al final de cada comando puede llegar a ser
                # lento si hay varios comandos encolados.

                buf.commit()

                prot.lastHandledPacket = time.time()

            except:
                buf.rollback()
                raise
        except ByteQueueError, e:
            pass
            debug_print("ByteQueueError", e)
        except ByteQueueInsufficientData, e:
            pass
        except CommandsDecoderException, e:
            pass
            # debug_print("CommandsDecoderException")
        except Exception, e:
            debug_print("handleData Exception: ", e)
            raise

    def CheckLogged(fOrig):
        """Decorator para verificar que el usuario esta logeado"""
        def fNew(self, prot, buf):
            if prot.player is None:
                raise CriticalDecoderException()
            return fOrig(self, prot, buf, prot.player)
        return fNew

    def CheckNotLogged(fOrig):
        """Decorator para verificar que el usuario no esta logeado"""
        def fNew(self, prot, buf):
            if prot.player is not None:
                raise CriticalDecoderException()
            return fOrig(self, prot, buf, None)
        return fNew

    @CheckNotLogged
    def handleCmdLoginExistingChar(self, prot, buf, player):
        # PacketID
        cmd = buf.readInt8()

        playerName = buf.readString()
        playerPass = buf.readString()
        playerVers = '%d.%d.%d' % (buf.readInt8(), buf.readInt8(),\
            buf.readInt8())

        error = False

        if not isValidPlayerName(playerName, False):
            error = True
            debug_print("Nombre invalido:", repr(playerName))
        elif cv.gameServer.playersLimitReached():
            error = True
        else:
            # La instancia de Player se crea recien cuando es válido.
            prot.player = Player(prot, playerName)
            prot.player.start()

        if error:
            prot.loseConnection()

    @CheckNotLogged
    def handleCmdThrowDices(self, prot, buf, player):
        raise CriticalDecoderException("Not Implemented")

    @CheckNotLogged
    def handleCmdLoginNewChar(self, prot, buf, player):
        raise CriticalDecoderException("Not Implemented")

    @CheckLogged
    def handleCmdTalk(self, prot, buf, player):
        # PacketID
        cmd = buf.readInt8()
        msg = buf.readString()
        # FIXME
        for p in cv.gameServer.playersList():
            p.cmdout.sendConsoleMsg(player.playerName + " dice: " + msg)

    @CheckLogged
    def handleCmdWalk(self, prot, buf, player):
        cmd = buf.readInt8()
        heading = buf.readInt8()
        # FIXME

    @CheckLogged
    def handleCmdOnline(self, prot, buf, player):
        cmd = buf.readInt8()
        player.cmdout.sendConsoleMsg(\
            "Online: %d" % cv.gameServer.playersCount())

    @CheckLogged
    def handleCmdQuit(self, prot, buf, player):
        cmd = buf.readInt8()
        player.quit()

    @CheckLogged
    def handleCmdYell(self, prot, buf, player):
        cmd = buf.readInt8()
        msg = buf.readString()
        # FIXME

    @CheckLogged
    def handleCmdWhisper(self, prot, buf, player):
        cmd = buf.readInt8()
        target = buf.readInt16()
        msg = buf.readString()
        # FIXME

    @CheckLogged
    def handleCmdRequestPositionUpdate(self, prot, buf, player):
        cmd = buf.readInt8()
        # FIXME

    @CheckLogged
    def handleCmdAttack(self, prot, buf, player):
        cmd = buf.readInt8()
        # FIXME

    @CheckLogged
    def handleCmdPickUp(self, prot, buf, player):
        cmd = buf.readInt8()
        # FIXME

    @CheckLogged
    def handleCmdSafeToggle(self, prot, buf, player):
        cmd = buf.readInt8()
        # FIXME

    @CheckLogged
    def handleCmdResuscitationSafeToggle(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestGuildLeaderInfo(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestAtributes(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestFame(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestSkills(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestMiniStats(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCommerceEnd(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdUserCommerceEnd(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdUserCommerceConfirm(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCommerceChat(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdBankEnd(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdUserCommerceOk(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdUserCommerceReject(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdDrop(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCastSpell(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdLeftClick(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdDoubleClick(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdWork(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdUseSpellMacro(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdUseItem(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCraftBlacksmith(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCraftCarpenter(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdWorkLeftClick(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCreateNewGuild(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdSpellInfo(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdEquipItem(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdChangeHeading(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdModifySkills(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdTrain(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCommerceBuy(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdBankExtractItem(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCommerceSell(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdBankDeposit(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdForumPost(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdMoveSpell(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdMoveBank(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdClanCodexUpdate(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdUserCommerceOffer(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildAcceptPeace(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildRejectAlliance(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildRejectPeace(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildAcceptAlliance(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildOfferPeace(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildOfferAlliance(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildAllianceDetails(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildPeaceDetails(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildRequestJoinerInfo(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildAlliancePropList(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildPeacePropList(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildDeclareWar(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildNewWebsite(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildAcceptNewMember(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildRejectNewMember(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildKickMember(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildUpdateNews(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildMemberInfo(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildOpenElections(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildRequestMembership(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildRequestDetails(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdOnline(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdQuit(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildLeave(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestAccountState(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPetStand(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPetFollow(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdReleasePet(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdTrainList(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRest(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdMeditate(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdResucitate(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdHeal(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdHelp(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestStats(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCommerceStart(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdBankStart(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdEnlist(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdInformation(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdReward(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestMOTD(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdUpTime(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartyLeave(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartyCreate(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartyJoin(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdInquiry(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildMessage(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartyMessage(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCentinelReport(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildOnline(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartyOnline(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCouncilMessage(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRoleMasterRequest(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGMRequest(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdbugReport(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdChangeDescription(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildVote(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPunishments(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdChangePassword(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGamble(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdInquiryVote(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdLeaveFaction(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdBankExtractGold(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdBankDepositGold(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdDenounce(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildFundate(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildFundation(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartyKick(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartySetLeader(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartyAcceptMember(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPing(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestPartyForm(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdItemUpgrade(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGMCommands(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdInitCrafting(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdHome(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdShowGuildNews(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdShareNpc(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdStopSharingNpc(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdConsultation(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

class ServerCommandsEncoder(object):
    """
    Conjunto de funciones para generar comandos hacia el cliente.
    """

    __slots__ = ('buf', 'prot', )

    def __init__(self, prot):
        self.buf = prot.outbuf
        self.prot = prot # K-Pax.

    def sendConsoleMsg(self, msg, font=0):
        self.buf.writeInt8(serverPackets['ConsoleMsg'])
        self.buf.writeString(msg)
        self.buf.writeInt8(font)

        self.prot.flushOutBuf()

    def sendLogged(self, userClass):
        self.buf.writeInt8(serverPackets['Logged'])
        self.buf.writeInt8(userClass)

        self.prot.flushOutBuf()

    def sendChangeMap(self, n, vers):
        self.buf.writeInt8(serverPackets['ChangeMap'])
        self.buf.writeInt16(n)
        self.buf.writeInt16(vers)

        self.prot.flushOutBuf()

    def sendUserIndexInServer(self, n):
        self.buf.writeInt8(serverPackets['UserIndexInServer'])
        self.buf.writeInt16(n)

        self.prot.flushOutBuf()

    def sendUserCharIndexInServer(self, n):
        self.buf.writeInt8(serverPackets['UserCharIndexInServer'])
        self.buf.writeInt16(n)

        self.prot.flushOutBuf()

